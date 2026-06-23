"""Higgsfield video provider (image -> short cinematic clip).

REST API (platform.higgsfield.ai):
  auth    Authorization: Key KEY_ID:KEY_SECRET
  img2vid POST /{model_path}  {"image_url": "...", "prompt": "...", "duration": N}
  status  GET  /requests/{id}/status -> {video:{url}} or {status, video:{url}}

Env vars:
  HIGGSFIELD_KEY_ID    key ID  (default: 745f4f41-b5ba-4f2f-a2f8-acbd28de30e9)
  HIGGSFIELD_API_KEY   key secret  (required)
  HIGGSFIELD_BASE      default https://platform.higgsfield.ai
  HIGGSFIELD_MODEL_PATH default /higgsfield-ai/dop/standard
  HIGGSFIELD_DURATION  default 5
"""
import os, json, time, urllib.request
from studio.host import upload

KEY_ID = os.getenv("HIGGSFIELD_KEY_ID", "745f4f41-b5ba-4f2f-a2f8-acbd28de30e9")
API_KEY = os.getenv("HIGGSFIELD_API_KEY", "")
BASE = os.getenv("HIGGSFIELD_BASE", "https://platform.higgsfield.ai").rstrip("/")
MODEL_PATH = os.getenv("HIGGSFIELD_MODEL_PATH", "/higgsfield-ai/dop/standard")
DURATION = int(os.getenv("HIGGSFIELD_DURATION", "5"))


def configured() -> bool:
    return bool(API_KEY)


def _auth_header() -> dict:
    # If API_KEY already contains ":" it's already KEY_ID:SECRET, use as-is
    token = API_KEY if ":" in API_KEY else f"{KEY_ID}:{API_KEY}"
    return {"Authorization": f"Key {token}", "Content-Type": "application/json"}


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
        raise RuntimeError("HIGGSFIELD_API_KEY required")
    img_url = upload(image_path, filename="frame.png")
    prompt = (motion_prompt or "") + ", subtle minimal cinematic motion, keep the character stable"
    payload = {"image_url": img_url, "prompt": prompt, "duration": DURATION}
    req = urllib.request.Request(BASE + MODEL_PATH, data=json.dumps(payload).encode(),
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
