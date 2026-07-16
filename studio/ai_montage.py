"""ИИ-монтаж из сырья: брось клипы + фото + промт → профессиональный монтаж.

Движок — FFmpeg (то, что оборачивают MCP-серверы видеомонтажа). Мозги — LLM
(OpenRouter, регион-ок). Пайплайн:
  1. собираем метаданные ассетов (длительности клипов);
  2. LLM по промту + списку ассетов строит ПЛАН монтажа (JSON: сегменты, обрезки,
     вставки фото, подписи, переходы, музыка);
  3. FFmpeg исполняет план -> готовый вертикальный ролик 9:16.
"""
import os
import json
import subprocess
import urllib.request
from studio import ffbin
from studio import compose, edit

FF = ffbin.resolve()
W, H = 720, 1280
OPENROUTER_KEY_ENV = "OPENROUTER_API_KEY"
EDIT_MODEL = os.getenv("OR_EDIT_MODEL", "meta-llama/llama-3.3-70b-instruct")


def _is_video(p):
    return p.lower().rsplit(".", 1)[-1] in ("mp4", "mov", "webm", "mkv", "avi")


def probe(assets: list[str]) -> list[dict]:
    """Метаданные ассетов: тип + длительность (для видео)."""
    out = []
    for a in assets:
        if _is_video(a):
            out.append({"src": a, "type": "video", "duration": round(edit._duration(a), 2)})
        else:
            out.append({"src": a, "type": "photo"})
    return out


SYS = (
    "Ты — профессиональный видеомонтажёр коротких вертикальных роликов (9:16, Shorts/Reels). "
    "Тебе дают список сырых ассетов (видеоклипы с длительностью и фото) и задание. "
    "Собери монтажный план: выбери порядок, обрежь куски (in/out в секундах в пределах длительности), "
    "вставь фото как короткие кадры, добавь к каждому сегменту короткую подпись (caption, 2-5 слов, без опечаток) "
    "и ключевое слово эмфазы. Делай динамично: короткие сегменты (1.5–4с), сильный первый кадр (хук), смысловой финал.\n"
    "Верни СТРОГО JSON:\n"
    '{"segments":[{"src":"<имя файла из списка>","type":"video|photo","in":0.0,"out":3.0,'
    '"duration":2.0,"caption":"","emphasis":""}],"transition":"fade|none"}\n'
    "Для video указывай in/out; для photo — duration (1.5–3с). Только JSON, без пояснений."
)


def plan_montage(asset_meta: list[dict], prompt: str) -> dict:
    key = os.getenv(OPENROUTER_KEY_ENV)
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY required")
    lst = "\n".join(
        f"- {os.path.basename(a['src'])} | {a['type']}" + (f" | {a['duration']}с" if a.get("duration") else "")
        for a in asset_meta)
    user = f"Задание: {prompt}\n\nАссеты:\n{lst}\n\nСобери монтажный план JSON."
    body = {"model": EDIT_MODEL, "temperature": 0.4, "max_tokens": 1800,
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": user}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    raw = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]["content"]
    s, e = raw.find("{"), raw.rfind("}")
    if s < 0:
        raise RuntimeError(f"LLM не вернул JSON: {raw[:200]}")
    return json.loads(raw[s:e+1])


def _burn_caption(clip: str, caption: str, out: str):
    """Чистая статичная подпись внизу кадра (на весь сегмент)."""
    if not caption.strip():
        subprocess.run([FF, "-y", "-i", clip, "-c", "copy", out], capture_output=True)
        return out
    capf = out + ".txt"; open(capf, "w", encoding="utf-8").write(caption.strip().upper())
    vf = (f"drawtext=textfile='{capf}':fontfile='{compose.FONT}':fontsize=52:fontcolor=white:"
          f"borderw=4:bordercolor=black:x=(w-tw)/2:y=h-300:line_spacing=10")
    subprocess.run([FF, "-y", "-i", clip, "-vf", vf, "-an", "-r", "30",
                    "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", out], capture_output=True)
    return out


def execute_plan(plan: dict, assets: list[str], out_path: str, workdir: str,
                 music: str | None = None) -> dict:
    """Исполнить монтажный план FFmpeg-ом -> готовый ролик."""
    os.makedirs(workdir, exist_ok=True)
    by_name = {os.path.basename(a): a for a in assets}
    seg_clips, t = [], 0.0
    for i, seg in enumerate(plan.get("segments", [])):
        src = by_name.get(os.path.basename(seg.get("src", "")))
        if not src or not os.path.exists(src):
            continue
        base = os.path.join(workdir, f"seg{i}_base.mp4")
        if seg.get("type") == "photo" or not _is_video(src):
            dur = float(seg.get("duration", 2.0))
            compose.mock_clip(src, "", dur, base)
        else:
            tin = float(seg.get("in", 0)); tout = float(seg.get("out", tin + 3))
            dur = max(0.5, tout - tin)
            tmp = os.path.join(workdir, f"raw{i}.mp4")
            subprocess.run([FF, "-y", "-ss", f"{tin}", "-i", src, "-t", f"{dur:.2f}",
                            "-an", tmp], capture_output=True)
            edit.trim(tmp, dur, base)
        sv = os.path.join(workdir, f"seg{i}.mp4")
        _burn_caption(base, seg.get("caption", ""), sv)   # чистая подпись на сегмент
        seg_clips.append(sv)
        t += dur
    if not seg_clips:
        raise RuntimeError("план пуст — нет валидных сегментов")
    vcat = os.path.join(workdir, "vcat.mp4")
    if plan.get("transition") == "fade" and len(seg_clips) > 1:
        edit.xfade_stitch(seg_clips, vcat, trans=0.3)
    else:
        _concat(seg_clips, vcat, workdir)
    narration = os.path.join(workdir, "silent.m4a"); compose.silence(narration, t)
    edit.finalize(vcat, narration, out_path, ass=None, music=music)
    return {"out": out_path, "segments": len(seg_clips), "duration": round(t, 2)}


def _concat(clips, out, workdir):
    lst = os.path.join(workdir, "c.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in clips))
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-r", "30", out], capture_output=True)
    return out


def ai_montage(assets: list[str], prompt: str, out_path: str, workdir: str,
               music: str | None = None) -> dict:
    meta = probe(assets)
    plan = plan_montage(meta, prompt)
    res = execute_plan(plan, assets, out_path, workdir, music)
    res["plan"] = plan
    return res
