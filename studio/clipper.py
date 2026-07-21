"""Нарезка длинного видео на вертикальные Shorts.

Пайплайн (переиспользует наш стек: faster-whisper + OpenRouter LLM + ffmpeg + караоке):
  1. транскрибируем всё видео (слова с таймкодами);
  2. LLM выбирает N самодостаточных «цепляющих» фрагментов (20-60с) + заголовок к каждому;
  3. каждый фрагмент режем, ревреймим 16:9 -> 9:16 (центр-кроп), жжём субтитры и хук-заголовок.
Выход — несколько готовых Shorts. Тяжёлое (whisper на длинном видео) — гоняется на воркере.
"""
import json
import os
import subprocess
import urllib.request

from studio import ffbin, edit

FF = ffbin.resolve()
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
PLAN_MODEL = os.getenv("CLIPPER_MODEL", os.getenv("FACTORY_TEXT_MODEL", "anthropic/claude-sonnet-4.5"))
W, H = 1080, 1920                      # 9:16


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _transcribe(path, wd):
    from studio.assemble import _transcribe as _t
    return _t(path, wd)                 # words, lines, lang


def _pick_segments(lines, total, n, min_s, max_s):
    """LLM выбирает лучшие моменты. Возвращает [{start,end,title}]."""
    sys_p = (
        "Ты — редактор коротких вертикальных видео (Shorts/Reels). Тебе дают транскрипт "
        "длинного видео с таймкодами (сек). Выбери самые сильные, САМОДОСТАТОЧНЫЕ фрагменты, "
        "которые работают как отдельный ролик: цельная мысль/история/инсайт с зацепкой в начале.\n"
        f"Правила: {min_s}-{max_s} секунд каждый; не пересекаются; разнесены по видео; "
        "начинай на осмысленной фразе (не с середины слова). К каждому дай короткий цепляющий "
        "русский заголовок (до 60 симв.).\n"
        f"Верни ТОЛЬКО JSON-массив ровно из {n} объектов: "
        '[{"start": сек, "end": сек, "title": "заголовок", "why": "чем цепляет"}]'
    )
    usr = f"Длительность видео: {total:.0f}с.\n\nТРАНСКРИПТ:\n{lines[:16000]}"
    body = {"model": PLAN_MODEL, "temperature": 0.5, "messages": [
        {"role": "system", "content": sys_p}, {"role": "user", "content": usr}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"})
    txt = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]["content"].strip()
    if "```" in txt:
        txt = txt.split("```")[1]
        if txt.lstrip().startswith("json"):
            txt = txt.lstrip()[4:]
    a, b = txt.find("["), txt.rfind("]")
    raw = json.loads(txt[a:b + 1])
    segs = []
    for it in raw:
        s, e = float(it["start"]), float(it["end"])
        if e - s < min_s * 0.6 or s >= total:
            continue
        e = min(e, s + max_s, total)
        segs.append({"start": s, "end": e, "title": str(it.get("title", "")).strip()[:60]})
    return segs[:n]


def _words_in(words, s, e):
    return [[w[0], w[1] - s, w[2] - s] for w in words if w[1] >= s and w[2] <= e]


def _src_wh(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "default=nk=1:nw=1", src],
                       capture_output=True, text=True)
    nums = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    if len(nums) >= 2:
        return nums[0], nums[1]
    return 1920, 1080


def _face_center_x(src, s, e, wd, idx, samples=9):
    """Устойчивый центр лица спикера по X (0..1) для реврейма. None если лиц не нашли.
    Семплим кадры, детектим Haar-каскадом фронтальные лица, берём медиану центров
    крупнейшего лица (взвешенно по площади). Без cv2 / при ошибке -> None (центр-кроп)."""
    try:
        import cv2
        CC = getattr(cv2, "CascadeClassifier", None) or getattr(getattr(cv2, "objdetect", None), "CascadeClassifier", None)
        if CC is None:
            return None                                 # сборка cv2 без objdetect -> центр-кроп
        cascade = CC(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if cascade.empty():
            return None
    except Exception:
        return None                                     # любая проблема cv2 -> безопасный центр-кроп
    centers, weights = [], []
    for i in range(samples):
        t = s + (e - s) * (i + 0.5) / samples
        f = os.path.join(wd, f"face{idx}_{i}.png")
        subprocess.run([FF, "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                        "-vf", "scale=640:-1", f], capture_output=True)
        if not os.path.exists(f):
            continue
        try:
            img = cv2.imread(f)
            os.remove(f)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
            if len(faces) == 0:
                continue
            fw = img.shape[1]
            x, y, w, h = max(faces, key=lambda r: r[2] * r[3])   # крупнейшее лицо
            centers.append((x + w / 2) / fw)
            weights.append(w * h)
        except Exception:
            continue
    if not centers:
        return None
    # взвешенная медиана (устойчивее среднего к скачкам между спикерами)
    order = sorted(range(len(centers)), key=lambda i: centers[i])
    tot = sum(weights); acc = 0
    for i in order:
        acc += weights[i]
        if acc >= tot / 2:
            return centers[i]
    return centers[order[-1]]


def _cut_reframe(src, s, e, out, title, words, captions, wd, idx):
    """Вырезать [s,e], реврейм 16:9 -> 9:16 вокруг лица спикера, субтитры и хук-заголовок —
    всё ОДНИМ проходом ffmpeg (надёжнее двухпроходной схемы с промежуточным файлом)."""
    seg_words = _words_in(words, s, e)
    sw, sh = _src_wh(src)
    cw = int(sh * 9 / 16) & ~1                          # чётная ширина кроп-окна
    fx = _face_center_x(src, s, e, wd, idx)
    cx = (sw - cw) // 2 if fx is None else max(0, min(int(fx * sw - cw / 2), sw - cw))

    vf = [f"crop={cw}:{sh}:{cx}:0", f"scale={W}:{H}"]
    if captions and seg_words:
        ass = os.path.join(wd, f"cap{idx}.ass")
        edit.karaoke_ass(seg_words, ass, group=3)
        ap = ass.replace("\\", "/").replace(":", "\\:")
        fd = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts"))
        vf.append(f"ass={ap}:fontsdir='{fd}'")
    if title:
        from studio.compose import _wrap
        tf = out + ".title.txt"
        open(tf, "w", encoding="utf-8").write(_wrap(title.upper(), width=18))
        FONT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts", "DejaVuSans.ttf"))
        vf.append(f"drawtext=textfile='{tf}':fontfile='{FONT}':fontsize=54:fontcolor=white:"
                  f"borderw=6:bordercolor=black:box=1:boxcolor=black@0.4:boxborderw=20:"
                  f"line_spacing=10:x=(w-tw)/2:y=140")
    # -ss/-t как ВЫХОДНЫЕ опции после -i: точная и корректная обрезка [s, e]
    ffbin.run_checked([FF, "-y", "-i", src, "-ss", f"{s:.2f}", "-t", f"{max(0.5, e - s):.2f}",
                       "-vf", ",".join(vf), "-c:v", "libx264", "-threads", "2", "-preset", "veryfast",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", out], out_path=out)
    return out


def clip_to_shorts(video_path, out_dir, workdir, n=5, progress=None, captions=True,
                   min_s=20, max_s=60):
    def p(m, pct):
        if progress:
            progress(m, pct)

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)
    total = _dur(video_path)

    p("транскрибирую видео (самый долгий этап)", 8)
    words, lines, lang = _transcribe(video_path, workdir)

    p("выбираю лучшие моменты", 55)
    segs = _pick_segments(lines, total, n, min_s, max_s)
    if not segs:
        raise RuntimeError("LLM не выбрал ни одного фрагмента")

    results = []
    for i, seg in enumerate(segs):
        p(f"нарезаю Short {i+1}/{len(segs)}: {seg['title']}", 60 + int(38 * i / len(segs)))
        out = os.path.join(out_dir, f"short{i}.mp4")
        _cut_reframe(video_path, seg["start"], seg["end"], out, seg["title"], words, captions, workdir, i)
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            results.append({"path": out, "title": seg["title"],
                            "start": round(seg["start"], 1), "end": round(seg["end"], 1)})
    p("готово", 100)
    return {"shorts": results, "lang": lang, "duration": total, "count": len(results)}
