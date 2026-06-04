"""Image generation provider (text->image, image+refs->image).

Default: OpenRouter Gemini image model (works without a new account, uses existing
OpenRouter credits, region-ok). Reference images keep characters/style consistent.
"""
import os, json, base64, urllib.request

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
IMAGE_MODEL = os.getenv("OR_IMAGE_MODEL", "google/gemini-2.5-flash-image")


def _data_url(path: str) -> str:
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def generate_image(prompt: str, out_path: str, refs: list[str] | None = None) -> str:
    """Generate an image from a prompt (+ optional reference image paths) -> out_path."""
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_API_KEY required for image generation")
    content = [{"type": "text", "text": prompt}]
    for r in (refs or []):
        content.append({"type": "image_url", "image_url": {"url": _data_url(r)}})
    body = {"model": IMAGE_MODEL, "modalities": ["image", "text"],
            "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                                          "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    imgs = r.get("choices", [{}])[0].get("message", {}).get("images") or []
    if not imgs:
        raise RuntimeError(f"no image returned: {json.dumps(r)[:200]}")
    data = imgs[0]["image_url"]["url"].split(",", 1)[1]
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data))
    return out_path
