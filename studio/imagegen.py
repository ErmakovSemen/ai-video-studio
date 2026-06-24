"""Image generation — three backends, auto-selected by available env key.

Priority:
  1. GEMINI_API_KEY  → Gemini 2.0 Flash image gen (free tier, 1500 req/day)
  2. HF_TOKEN        → FLUX.1-schnell via HF Inference API (free, rate-limited)
  3. OPENROUTER_API_KEY → OpenRouter (model from OR_IMAGE_MODEL env / per-call override)
"""
import os, json, base64, urllib.request

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# Default: free OpenRouter model. Override per-call or via env.
IMAGE_MODEL = os.getenv("OR_IMAGE_MODEL", "google/gemini-2.5-flash-image")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

IMAGE_MODELS = [
    {"id": "google/gemini-2.5-flash-image", "name": "Gemini 2.5 Flash Image",
     "cost": "~$0.004/кадр", "cost_usd": 0.004, "note": "рекомендуется, refs ✓", "badge": "DEFAULT"},
    {"id": "google/gemini-2.5-flash-image", "name": "Gemini 2.5 Flash Image",
     "cost": "~$0.004/кадр", "cost_usd": 0.004, "note": "лучше качество, refs ✓"},
    {"id": "openai/dall-e-3", "name": "DALL-E 3",
     "cost": "~$0.04/кадр", "cost_usd": 0.04, "note": "топ качество, без refs"},
    {"id": "stabilityai/stable-diffusion-3-5-large", "name": "Stable Diffusion 3.5",
     "cost": "~$0.01/кадр", "cost_usd": 0.01, "note": "без refs"},
]


def _data_url(path: str) -> str:
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def _b64(path: str) -> str:
    return base64.b64encode(open(path, "rb").read()).decode()


def _gemini(prompt: str, out_path: str, refs: list[str] | None = None) -> str:
    parts = [{"text": prompt}]
    for r in (refs or []):
        parts.append({"inline_data": {"mime_type": "image/png", "data": _b64(r)}})
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        f"/gemini-2.0-flash-preview-image-generation:generateContent?key={GEMINI_KEY}"
    )
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    resp = json.load(urllib.request.urlopen(req, timeout=120))
    for part in resp["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(part["inlineData"]["data"]))
            return out_path
    raise RuntimeError(f"Gemini: no image in response: {json.dumps(resp)[:300]}")


def _hf(prompt: str, out_path: str, refs: list[str] | None = None) -> str:
    url = f"https://router.huggingface.co/hf-inference/models/{HF_IMAGE_MODEL}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"inputs": prompt}).encode(),
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
    )
    data = urllib.request.urlopen(req, timeout=120).read()
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def _openrouter(prompt: str, out_path: str, refs: list[str] | None = None,
                model: str | None = None) -> str:
    m = model or IMAGE_MODEL
    content = [{"type": "text", "text": prompt}]
    for r in (refs or []):
        content.append({"type": "image_url", "image_url": {"url": _data_url(r)}})
    body = {
        "model": m,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": content}],
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
    )
    r = json.load(urllib.request.urlopen(req, timeout=120))
    imgs = r.get("choices", [{}])[0].get("message", {}).get("images") or []
    if not imgs:
        raise RuntimeError(f"OpenRouter: no image returned: {json.dumps(r)[:200]}")
    data = imgs[0]["image_url"]["url"].split(",", 1)[1]
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data))
    return out_path


def generate_image(prompt: str, out_path: str, refs: list[str] | None = None,
                   model: str | None = None) -> str:
    """Generate an image. Backend chosen by available env key (see module docstring).

    model: override OpenRouter model for this call (ignored for Gemini/HF backends).
    """
    if GEMINI_KEY:
        return _gemini(prompt, out_path, refs)
    if HF_TOKEN:
        return _hf(prompt, out_path, refs)
    if OPENROUTER_KEY:
        return _openrouter(prompt, out_path, refs, model=model)
    raise RuntimeError(
        "No image-gen key found. Set GEMINI_API_KEY (free) or HF_TOKEN (free) or OPENROUTER_API_KEY."
    )
