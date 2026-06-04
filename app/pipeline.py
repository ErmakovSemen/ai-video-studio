"""Reusable AI video pipeline.

Steps: (OpenRouter) prompt refine -> (FAL Flux) image [or user image] ->
(FAL Kling) image-to-video -> (edge-tts) voice -> (ffmpeg) stitch -> mp4.

Pluggable: if FAL_KEY is missing, runs in MOCK mode (Ken-Burns on the input
image / gradient + voice) so the UI and flow work end-to-end without a key.
Swap the FAL adapter for another provider without touching the UI/orchestration.
"""
import os, asyncio, subprocess, tempfile, textwrap, math
import httpx
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

FF = imageio_ffmpeg.get_ffmpeg_exe()
FAL_KEY = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
FLUX_MODEL = os.getenv("FAL_FLUX_MODEL", "fal-ai/flux/schnell")
KLING_MODEL = os.getenv("FAL_KLING_MODEL", "fal-ai/kling-video/v1.6/standard/image-to-video")
VOICE = os.getenv("TTS_VOICE", "ru-RU-DmitryNeural")
# Free image-to-video via a public Hugging Face Space (no key, no payment, no region).
HF_VIDEO_SPACE = os.getenv("HF_VIDEO_SPACE", "Daankular/Sulphur")
HF_ENABLED = os.getenv("HF_ENABLED", "1") != "0"
W, H = 1080, 1920


def mode() -> str:
    """fal (paid, best) > hf (free Spaces) > mock (no network gen)."""
    if FAL_KEY:
        return "fal"
    if HF_ENABLED:
        try:
            import gradio_client  # noqa: F401
            return "hf"
        except Exception:
            return "mock"
    return "mock"


# ---------------- OpenRouter (prompt refine) ----------------
async def refine_prompt(description: str) -> str:
    """Turn a rough description into a vivid visual prompt (optional)."""
    if not OPENROUTER_KEY:
        return description
    try:
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                json={
                    "model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"),
                    "messages": [
                        {"role": "system", "content": "Ты помогаешь делать промпты для генерации видео. Верни ОДИН короткий насыщенный визуальный промпт на английском, без пояснений."},
                        {"role": "user", "content": description},
                    ],
                    "max_tokens": 120,
                },
            )
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return description


# ---------------- FAL adapter ----------------
def _fal_client():
    import fal_client  # imported lazily; only needed in fal mode
    os.environ["FAL_KEY"] = FAL_KEY
    return fal_client


def fal_text_to_image(prompt: str) -> str:
    fc = _fal_client()
    res = fc.subscribe(FLUX_MODEL, arguments={"prompt": prompt, "image_size": "portrait_16_9"})
    return res["images"][0]["url"]


def fal_image_to_video(image_url: str, prompt: str, duration: int = 5) -> str:
    fc = _fal_client()
    res = fc.subscribe(KLING_MODEL, arguments={
        "prompt": prompt, "image_url": image_url, "duration": str(duration),
        "aspect_ratio": "9:16",
    })
    return res["video"]["url"]


def fal_upload(path: str) -> str:
    fc = _fal_client()
    return fc.upload_file(path)


# ---------------- Free HF Space adapter (image-to-video) ----------------
def hf_image_to_video(image_path: str, prompt: str, out_path: str):
    """Animate a still image into a short vertical clip via a free public HF Space.
    Proven anonymous (no token). Free ZeroGPU => may queue / be slow / rate-limit.
    """
    from gradio_client import Client, handle_file
    import shutil
    c = Client(HF_VIDEO_SPACE)
    res = c.predict(
        image=handle_file(image_path),
        prompt=prompt,
        model_choice="Sulphur 2 Base",
        resolution="576x1024",
        steps=6, guidance_scale=4.0, frames=49, seed=-1,
        api_name="/generate_video",
    )
    src = res[0] if isinstance(res, (list, tuple)) else res
    shutil.copy(src, out_path)


def _download(url: str, path: str):
    with httpx.stream("GET", url, timeout=300) as r:
        with open(path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)


# ---------------- voice ----------------
async def tts(text: str, path: str):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="+8%").save(path)


def audio_dur(path: str) -> float:
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    import re
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return float(m[1])*3600 + float(m[2])*60 + float(m[3]) if m else 6.0


# ---------------- MOCK clip (no FAL) ----------------
def _gradient_image(text: str, path: str):
    arr = np.zeros((H, W, 3), np.uint8)
    y = np.linspace(0, 1, H)[:, None]
    arr[:] = (np.array([26, 19, 33]) * (1 - y) + np.array([9, 9, 13]) * y).astype(np.uint8)[:, None, :]
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    from PIL import ImageFont
    f = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", 64)
    wrapped = textwrap.fill(text, 22)
    d.multiline_text((W//2, H//2), wrapped, font=f, fill=(245, 245, 247),
                     anchor="mm", align="center", spacing=18)
    img.save(path)


def mock_clip(image_path: str | None, prompt: str, out: str, seconds: float):
    """Ken-Burns zoom on the input image (or a gradient with text)."""
    src = image_path
    tmp = None
    if not src:
        tmp = out + ".bg.png"
        _gradient_image(prompt, tmp)
        src = tmp
    d = max(2, int(seconds * 30))
    subprocess.run([
        FF, "-y", "-loop", "1", "-i", src, "-t", str(seconds),
        "-vf", (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},zoompan=z='min(zoom+0.0009,1.18)':d={d}:s={W}x{H}:fps=30,"
                f"format=yuv420p"),
        "-c:v", "libx264", "-preset", "veryfast", out
    ], capture_output=True)
    if tmp and os.path.exists(tmp):
        os.remove(tmp)


# ---------------- stitch ----------------
def mux(video: str, audio: str, out: str):
    subprocess.run([FF, "-y", "-i", video, "-i", audio,
                    "-c:v", "copy", "-c:a", "aac", "-shortest", out],
                   capture_output=True)


# ---------------- orchestration ----------------
async def generate(description: str, image_path: str | None, narration: str | None,
                   out_path: str, workdir: str) -> dict:
    info = {"mode": mode()}
    prompt = await refine_prompt(description)
    info["prompt"] = prompt
    clip = os.path.join(workdir, "clip.mp4")
    voice_text = (narration or description).strip()
    voice_mp3 = os.path.join(workdir, "voice.mp3")
    await tts(voice_text, voice_mp3)
    seconds = max(4.0, min(audio_dur(voice_mp3) + 0.6, 20))

    m = mode()
    if m == "fal":
        if image_path:
            img_url = fal_upload(image_path)
        else:
            img_url = fal_text_to_image(prompt)
        info["image_url"] = img_url
        vid_url = fal_image_to_video(img_url, prompt, duration=5)
        info["video_url"] = vid_url
        _download(vid_url, clip)
    elif m == "hf":
        # image-to-video needs a still; use the user's image or a rendered one.
        src_img = image_path
        if not src_img:
            src_img = os.path.join(workdir, "still.png")
            _gradient_image(description, src_img)
        try:
            hf_image_to_video(src_img, prompt, clip)
        except Exception as e:
            info["hf_error"] = str(e)[:200]
            mock_clip(image_path, description, clip, seconds)  # graceful fallback
    else:
        mock_clip(image_path, description, clip, seconds)

    mux(clip, voice_mp3, out_path)
    info["out"] = out_path
    return info
