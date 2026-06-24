"""Video provider (image -> short video). Default: OpenRouter Kling (existing credits).

Switchable to cheaper models (Wan/Seedance) via OR_VIDEO_MODEL for volume.
"""
import os, json, time, uuid, urllib.request

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
VIDEO_MODEL = os.getenv("OR_VIDEO_MODEL", "kwaivgi/kling-v3.0-std")
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "openrouter").lower()


def animate(image_path: str, motion_prompt: str, out_path: str,
            model_path: str | None = None) -> str:
    """Dispatch image->video to the configured provider (openrouter | higgsfield)."""
    if VIDEO_PROVIDER == "higgsfield":
        from studio import higgsfield
        return higgsfield.animate(image_path, motion_prompt, out_path, model_path=model_path)
    return _animate_openrouter(image_path, motion_prompt, out_path)


def _public_url(path: str) -> str:
    b = "----c" + uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="reqtype"\r\n\r\nfileupload\r\n').encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="fileToUpload"; filename="i.png"\r\n'
             f'Content-Type: image/png\r\n\r\n').encode() + open(path, "rb").read() + b"\r\n"
    body += (f'--{b}--\r\n').encode()
    req = urllib.request.Request("https://catbox.moe/user/api.php", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return urllib.request.urlopen(req, timeout=120).read().decode().strip()


def _animate_openrouter(image_path: str, motion_prompt: str, out_path: str) -> str:
    """Animate a still image into a short 9:16 clip via OpenRouter video API."""
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_API_KEY required")
    h = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    img_url = _public_url(image_path)
    # subtle-motion hint reduces morphing artifacts on flat illustration
    prompt = motion_prompt + ", subtle minimal motion, keep shapes and character stable"
    payload = {"model": VIDEO_MODEL, "prompt": prompt, "aspect_ratio": "9:16",
               "frame_images": [{"type": "image_url", "image_url": {"url": img_url},
                                 "frame_type": "first_frame"}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/videos",
                                 data=json.dumps(payload).encode(),
                                 headers={**h, "Content-Type": "application/json"})
    job = json.load(urllib.request.urlopen(req, timeout=120))
    jid = job["id"]; poll = job.get("polling_url") or f"https://openrouter.ai/api/v1/videos/{jid}"
    for _ in range(60):
        time.sleep(6)
        s = json.load(urllib.request.urlopen(urllib.request.Request(poll, headers=h), timeout=60))
        sd = s.get("data", s)
        if sd.get("status") in ("completed", "succeeded", "success"):
            url = (sd.get("unsigned_urls") or
                   [f"https://openrouter.ai/api/v1/videos/{jid}/content?index=0"])[0]
            data = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300).read()
            with open(out_path, "wb") as f:
                f.write(data)
            return out_path
        if sd.get("status") in ("failed", "error", "canceled"):
            raise RuntimeError(f"video {sd.get('status')}: {str(sd)[:160]}")
    raise RuntimeError("video timeout")
