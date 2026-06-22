"""Higgsfield video provider (image -> short cinematic clip).

Canonical API (official higgsfield-js SDK):
  base    https://platform.higgsfield.ai
  auth    Authorization: Key KEY_ID:KEY_SECRET     (one env string "KEY_ID:KEY_SECRET")
  img2vid POST /v1/image2video/dop  {model, prompt, input_images:[{image_url}], motions:[...]}
  status  GET  /requests/{id}/status -> {status, results|video:{url}}

Everything is env-configurable so the exact host/model/path can be tuned without code:
  HIGGSFIELD_API_KEY   "KEY_ID:KEY_SECRET"   (required to actually call the paid API)
  HIGGSFIELD_BASE      default https://platform.higgsfield.ai
  HIGGSFIELD_PATH      default /v1/image2video/dop
  HIGGSFIELD_MODEL     default turbo
  HIGGSFIELD_AUTH      default "key"  ("key" -> "Key <v>", "bearer" -> "Bearer <v>")

Paid generator: it only runs when a key is set AND the final (non-draft) render path
calls it. Drafts/board "Сгенерировать видео" never touch it.
"""
import os, json, time, urllib.request
from studio.host import upload

API_KEY = os.getenv("HIGGSFIELD_API_KEY", "")
BASE = os.getenv("HIGGSFIELD_BASE", "https://platform.higgsfield.ai").rstrip("/")
PATH = os.getenv("HIGGSFIELD_PATH", "/v1/image2video/dop")
MODEL = os.getenv("HIGGSFIELD_MODEL", "turbo")
AUTH_SCHEME = os.getenv("HIGGSFIELD_AUTH", "key").lower()


def configured() -> bool:
    return bool(API_KEY)


def _auth_header() -> dict:
    scheme = "Bearer" if AUTH_SCHEME == "bearer" else "Key"
    return {"Authorization": f"{scheme} {API_KEY}", "Content-Type": "application/json"}


def _find_video_url(obj) -> str | None:
    """Pull a video URL out of a status response of unknown exact shape."""
    if isinstance(obj, dict):
        v = obj.get("video")
        if isinstance(v, dict) and v.get("url"):
            return v["url"]
        if obj.get("video_url"):
            return obj["video_url"]
        if obj.get("url") and str(obj.get("url")).lower().endswith((".mp4", ".mov", ".webm")):
            return obj["url"]
        for val in obj.values():
            u = _find_video_url(val)
            if u:
                return u
    elif isinstance(obj, list):
        for it in obj:
            u = _find_video_url(it)
            if u:
                return u
    return None


def animate(image_path: str, motion_prompt: str, out_path: str) -> str:
    """Animate a still into a short clip via Higgsfield. Same signature as video.animate."""
    if not configured():
        raise RuntimeError("HIGGSFIELD_API_KEY required (format KEY_ID:KEY_SECRET)")
    img_url = upload(image_path, filename="frame.png")     # durable public URL for the API
    prompt = (motion_prompt or "") + ", subtle minimal cinematic motion, keep the character stable"
    payload = {"model": MODEL, "prompt": prompt,
               "input_images": [{"type": "image_url", "image_url": img_url}],
               "aspect_ratio": "9:16"}
    req = urllib.request.Request(BASE + PATH, data=json.dumps(payload).encode(),
                                 headers=_auth_header())
    job = json.load(urllib.request.urlopen(req, timeout=120))
    rid = job.get("id") or job.get("request_id") or (job.get("data") or {}).get("id")
    if not rid:
        raise RuntimeError(f"higgsfield: no request id in {str(job)[:200]}")
    status_url = f"{BASE}/requests/{rid}/status"
    for _ in range(90):
        time.sleep(4)
        s = json.load(urllib.request.urlopen(
            urllib.request.Request(status_url, headers=_auth_header()), timeout=60))
        st = (s.get("status") or (s.get("data") or {}).get("status") or "").lower()
        if st in ("completed", "succeeded", "success"):
            url = _find_video_url(s)
            if not url:
                raise RuntimeError(f"higgsfield: completed but no video url in {str(s)[:200]}")
            data = urllib.request.urlopen(url, timeout=300).read()
            with open(out_path, "wb") as f:
                f.write(data)
            return out_path
        if st in ("failed", "error", "canceled", "nsfw"):
            raise RuntimeError(f"higgsfield {st}: {str(s)[:160]}")
    raise RuntimeError("higgsfield timeout")
