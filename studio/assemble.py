"""Нейромонтаж: несколько клипов -> нормализация -> склейка с переходами ->
распознавание речи -> ИИ-режиссёр планирует B-roll по промту -> генерация вставок ->
композитинг (full-frame cutaway с fade) -> опц. караоке-субтитры.

Собрано целиком на нашем стеке (ffmpeg + faster-whisper + imagegen) + один LLM-вызов
(OpenRouter) для плана вставок. progress(msg, pct) — колбэк для UI.
"""
import os, re, json, subprocess, urllib.request
from studio import edit, imagegen

FF = edit.FF
FPS = 30
XF = 0.5                       # длительность перехода между клипами
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
PLAN_MODEL = os.getenv("MONTAGE_LLM", "meta-llama/llama-3.3-70b-instruct")
_DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "docs", "montage_system_prompt.md")


def _broll_style(W, H):
    orient = "horizontal 16:9" if W > H else "vertical 9:16"
    return f"NO text no letters no words no captions, {orient} composition, high quality"


def _canvas(src):
    """Холст = аспект первого клипа (с учётом поворота), длинная сторона <= 1280. Без леттербокса."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height:stream_side_data=rotation",
                          "-of", "json", src], capture_output=True, text=True).stdout
    st = json.loads(out)["streams"][0]
    w, h = int(st["width"]), int(st["height"])
    for sd in st.get("side_data_list", []):
        if abs(int(sd.get("rotation", 0))) % 180 == 90:
            w, h = h, w
    sc = min(1.0, 1280 / max(w, h))
    return max(2, int(round(w * sc / 2)) * 2), max(2, int(round(h * sc / 2)) * 2)


def _load_sys():
    """Системный промт планировщика — из живого документа docs/montage_system_prompt.md."""
    try:
        txt = open(_DOC, encoding="utf-8").read()
        a = txt.index("## SYSTEM PROMPT")
        a = txt.index("\n", a) + 1
        b = txt.index("## VALIDATOR PROMPT")
        seg = txt[a:b].strip()
        if len(seg) > 100:
            return seg
    except Exception:
        pass
    return ("Ты — ИИ-режиссёр монтажа. Выбери 4-7 моментов для B-roll под сказанное. Исправляй "
            "ошибки терминов из ASR. Не ставь вставки поверх существующей графики. Верни ТОЛЬКО "
            "JSON-массив [{\"start\":сек,\"end\":сек,\"prompt\":\"english image prompt in the style\"}].")


def _dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=nk=1:nw=1", path], capture_output=True, text=True).stdout.strip() or 0)


def _scene_cuts(path, thr=0.32):
    """Таймкоды, где в основном видео меняется кадр (склейки/врезки)."""
    err = subprocess.run([FF, "-i", path, "-filter:v", f"select='gt(scene,{thr})',metadata=print",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    cuts = sorted({round(float(m.group(1)), 2) for m in re.finditer(r"pts_time:([\d.]+)", err)})
    return cuts


def _filter_plan(plan, cuts, total, min_gap_cut=1.0, min_spacing=4.0):
    """Убрать вставки вплотную к склейкам исходника и слишком частые; обрезать по склейкам."""
    plan = sorted(plan, key=lambda x: x["start"])
    kept = []
    for it in plan:
        s, e = it["start"], it["end"]
        if any(s - min_gap_cut < c < e + min_gap_cut for c in cuts):   # рядом со склейкой/поверх неё
            continue
        if kept and s - kept[-1]["start"] < min_spacing:               # слишком часто
            continue
        nxt = min([c for c in cuts if c > s] + [total])                # не заходить за следующую склейку
        it["end"] = min(e, nxt - 0.3, total - 0.1)
        if it["end"] - s >= 1.5:
            kept.append(it)
    return kept


def _normalize(src, wd, i, W, H):
    out = os.path.join(wd, f"norm{i}.mp4")
    # fill+crop по центру -> заполняем холст без чёрных полос (в т.ч. 16:9 -> 9:16)
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},setsar=1,fps={FPS}")
    subprocess.run([FF, "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2", out],
                   capture_output=True)
    return out


def _stitch(clips, wd):
    if len(clips) == 1:
        return clips[0]
    durs = [_dur(c) for c in clips]
    ins = []
    for c in clips:
        ins += ["-i", c]
    vparts, aparts, off, prev_v, prev_a = [], [], 0.0, "0:v", "0:a"
    for i in range(1, len(clips)):
        off = sum(durs[:i]) - XF * i
        vout = f"vx{i}"; aout = f"ax{i}"
        vparts.append(f"[{prev_v}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{vout}]")
        aparts.append(f"[{prev_a}][{i}:a]acrossfade=d={XF}[{aout}]")
        prev_v, prev_a = vout, aout
    out = os.path.join(wd, "stitched.mp4")
    subprocess.run([FF, "-y", *ins, "-filter_complex", ";".join(vparts + aparts),
                    "-map", f"[{prev_v}]", "-map", f"[{prev_a}]", "-c:v", "libx264",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", out], capture_output=True)
    return out


def _transcribe(path, wd):
    wav = os.path.join(wd, "audio.wav")
    subprocess.run([FF, "-y", "-i", path, "-ar", "16000", "-ac", "1", wav], capture_output=True)
    from faster_whisper import WhisperModel
    m = WhisperModel(os.getenv("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    segs, info = m.transcribe(wav, word_timestamps=True)
    words, lines = [], []
    for s in segs:
        lines.append(f"[{s.start:.1f}] {s.text.strip()}")
        for w in (s.words or []):
            words.append([w.word.strip(), float(w.start), float(w.end)])
    return words, "\n".join(lines), (info.language or "ru")


def _plan_broll(transcript, user_prompt, total, cuts=None):
    """LLM chooses B-roll insertion points. Falls back to even spacing if unavailable."""
    if OR_KEY:
        sys_p = _load_sys()
        cuts_s = ", ".join(f"{c:.1f}" for c in (cuts or [])) or "нет"
        usr = (f"ИНСТРУКЦИЯ: {user_prompt or 'сделай живее, добавь уместные вставки'}\n\n"
               f"СКЛЕЙКИ ОСНОВНОГО ВИДЕО (сек, не ставь вставки вплотную к ним и не поверх): {cuts_s}\n\n"
               f"ТРАНСКРИПТ:\n{transcript}")
        body = {"model": PLAN_MODEL, "messages": [{"role": "system", "content": sys_p},
                                                  {"role": "user", "content": usr}], "temperature": 0.4}
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=90))
            txt = r["choices"][0]["message"]["content"].strip()
            if "```" in txt:
                txt = txt.split("```")[1].lstrip("json").strip()
            start = txt.find("["); end = txt.rfind("]")
            plan = json.loads(txt[start:end + 1])
            clean = []
            for it in plan:
                s, e = float(it["start"]), float(it["end"])
                if 0.5 <= s < total and e > s:
                    clean.append({"start": s, "end": min(e, s + 3.6, total - 0.1), "prompt": str(it["prompt"])[:200]})
            if clean:
                return clean[:7]
        except Exception:
            pass
    # fallback: 3 evenly-spaced generic inserts
    n = 3
    step = total / (n + 1)
    return [{"start": round(step * (i + 1), 1), "end": round(step * (i + 1) + 3, 1),
             "prompt": "abstract calm concept illustration"} for i in range(n)]


def _composite(stitched, plan, out_path, captions, words, wd, W, H):
    if not plan:                               # нет безопасных вставок -> отдаём сшитое видео как есть
        if captions and words:
            ass = os.path.join(wd, "caps.ass"); edit.karaoke_ass(words, ass, group=3)
            ass_p = ass.replace("\\", "/").replace(":", "\\:")
            fonts = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
            subprocess.run([FF, "-y", "-i", stitched, "-vf", f"ass={ass_p}:fontsdir='{fonts}'",
                            "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", out_path],
                           capture_output=True)
        else:
            subprocess.run([FF, "-y", "-i", stitched, "-c:v", "libx264", "-preset", "medium",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", out_path], capture_output=True)
        return out_path
    inputs = ["-i", stitched]
    for it in plan:
        inputs += ["-loop", "1", "-i", it["img"]]
    fc, prev = [], "0:v"
    for i, it in enumerate(plan):
        s, e = it["start"], it["end"]
        fc.append(f"[{i+1}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"format=rgba,fade=t=in:st={s:.2f}:d=0.3:alpha=1,fade=t=out:st={e-0.3:.2f}:d=0.3:alpha=1[b{i}]")
    for i, it in enumerate(plan):
        fc.append(f"[{prev}][b{i}]overlay=0:0:enable='between(t,{it['start']:.2f},{it['end']:.2f})'[v{i}]")
        prev = f"v{i}"
    stage = out_path if not captions else os.path.join(wd, "nocap.mp4")
    subprocess.run([FF, "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]",
                    "-map", "0:a", "-c:a", "aac", "-c:v", "libx264", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-shortest", stage], capture_output=True)
    if captions and words:
        ass = os.path.join(wd, "caps.ass"); edit.karaoke_ass(words, ass, group=3)
        ass_p = ass.replace("\\", "/").replace(":", "\\:")
        fonts = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
        subprocess.run([FF, "-y", "-i", stage, "-vf", f"ass={ass_p}:fontsdir='{fonts}'",
                        "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", out_path],
                       capture_output=True)
    return out_path


def _spoken(words, it):
    s = " ".join(w for w, ws, we in words if ws < it["end"] and we > it["start"])
    return s.strip() or "(без слов)"


def assemble(video_paths, prompt, out_path, workdir, progress=None, captions=False,
             style="minimalist Asian ink wash on parchment", max_tries=3, aspect="source"):
    from studio import mvalidate
    LOG, regens = [], 0

    def p(m, pct):
        if progress:
            progress(m, pct)

    def logline(**kw):
        LOG.append(kw)
        print("ORCH " + json.dumps(kw, ensure_ascii=False), flush=True)

    def gen(prompt_txt, i, tag):
        img = os.path.join(workdir, f"broll{i}_{tag}.png")
        imagegen.generate_image(f"{prompt_txt}, {bstyle}", img)
        return img

    os.makedirs(workdir, exist_ok=True)
    if aspect == "9:16":
        W, H = 720, 1280
    elif aspect == "16:9":
        W, H = 1280, 720
    else:
        W, H = _canvas(video_paths[0])      # аспект как у оригинала
    bstyle = _broll_style(W, H)
    logline(canvas=f"{W}x{H}", style=style)
    p("Нормализую клипы", 6)
    normed = [_normalize(v, workdir, i, W, H) for i, v in enumerate(video_paths)]
    p("Сшиваю с переходами", 20)
    stitched = _stitch(normed, workdir)
    total = _dur(stitched)
    p("Распознаю речь", 32)
    words, transcript, lang = _transcribe(stitched, workdir)
    cuts = _scene_cuts(stitched)
    logline(scene_cuts=cuts)
    p("ИИ планирует вставки", 44)
    plan = _plan_broll(transcript, prompt, total, cuts)
    plan = _filter_plan(plan, cuts, total)
    logline(plan_after_filter=[{"t": round(it["start"], 1),
                                "concept": it.get("concept") or it["prompt"][:30]} for it in plan])

    # --- ЦИКЛ 1: генерация каждой вставки с валидацией смысла+стиля ---
    for i, it in enumerate(plan):
        p(f"Вставка {i+1}/{len(plan)}: генерация+проверка", 44 + int(30 * i / max(1, len(plan))))
        spoken = _spoken(words, it)
        cur_prompt = it["prompt"]
        best_img, best_score = None, -1
        for attempt in range(1, max_tries + 1):
            try:
                img = gen(cur_prompt, i, f"a{attempt}")
            except Exception as e:
                logline(insert=i, attempt=attempt, gen_error=str(e)[:80]); continue
            v = mvalidate.review_image(img, spoken, style)
            sc = int(v.get("score", 0))
            logline(insert=i, t=round(it["start"], 1), spoken=spoken[:70], attempt=attempt,
                    score=sc, ok=bool(v.get("ok")), reason=v.get("reason"), prompt=cur_prompt[:90])
            if sc > best_score:
                best_score, best_img = sc, img
            if v.get("ok"):
                break
            if attempt < max_tries:
                regens += 1
                cur_prompt = v.get("better_prompt") or cur_prompt
        it["img"] = best_img
    plan = [it for it in plan if it.get("img")]

    p("Собираю монтаж", 78)
    _composite(stitched, plan, out_path, captions, words, workdir, W, H)

    # --- ЦИКЛ 2: холистическая проверка склеек (картинки+таймлайны+текст) ---
    p("Проверяю склейки", 86)
    items = [{"i": i, "start": it["start"], "end": it["end"], "spoken": _spoken(words, it), "img": it["img"]}
             for i, it in enumerate(plan)]
    review = mvalidate.review_cuts(items, style)
    issues = review.get("issues", []) or []
    logline(phase="holistic_review", flagged=[{"index": x.get("index"), "reason": x.get("reason")} for x in issues])
    fixed = False
    for x in issues:
        i = x.get("index")
        if not isinstance(i, int) or i >= len(plan):
            continue
        it = plan[i]
        cur_prompt = x.get("better_prompt") or it["prompt"]
        try:
            img = gen(cur_prompt, i, "fix")
            v = mvalidate.review_image(img, _spoken(words, it), style)
            regens += 1
            logline(insert=i, phase="holistic_regen", score=int(v.get("score", 0)),
                    ok=bool(v.get("ok")), reason=v.get("reason"))
            it["img"] = img; fixed = True
        except Exception as e:
            logline(insert=i, phase="holistic_regen", gen_error=str(e)[:80])
    if fixed:
        p("Пересобираю монтаж", 94)
        _composite(stitched, plan, out_path, captions, words, workdir, W, H)

    p("Готово", 100)
    return {"duration": round(total, 1), "clips": len(video_paths), "inserts": len(plan),
            "lang": lang, "regens": regens, "log": LOG,
            "plan": [{"t": it["start"], "prompt": it["prompt"]} for it in plan]}
