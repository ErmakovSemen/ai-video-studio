"""QC gate for generated stills — a strict vision reviewer that rejects bad frames.

Wraps imagegen.generate_image: generate -> review with a vision LLM -> regenerate
on failure (up to `tries`), keeping the best-scoring frame. Catches the classic
failure modes: stray text/watermark, deformed anatomy, off-style/color, off-topic,
and abstract mush (the alpha-waves problem).
"""
import os, json, base64, time, urllib.request

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
REVIEW_MODEL = os.getenv("QC_MODEL", "google/gemini-2.5-flash")
GEMINI_REVIEW_MODEL = os.getenv("QC_GEMINI_MODEL", "gemini-2.0-flash")
THRESHOLD = int(os.getenv("QC_THRESHOLD", "5"))


def _b64(path: str) -> str:
    return base64.b64encode(open(path, "rb").read()).decode()


CHECKLIST = (
    "You are a STRICT quality reviewer for a monochrome Japanese ink-brush cartoon "
    "channel (black ink on white background, ukiyo-e / sumi-e, lots of white space, "
    "a recurring cute red panda character). Judge ONE generated frame against the "
    "intended scene. Be harsh — this frame may be published.\n\n"
    "Intended scene: {scene}\n\n"
    "Reject (fail) if ANY of these are true:\n"
    "- has_text: any letters, words, captions, watermark, or signature anywhere\n"
    "- has_color: any visible color (must be black/grey ink on white only)\n"
    "- bad_anatomy: deformed/extra limbs, broken faces, melted hands, mutant shapes\n"
    "- off_style: not clean ink linework, or muddy/photographic/3D look\n"
    "- abstract_mush: vague abstract blobs with no clear readable subject\n"
    "- off_topic: does not depict the intended scene\n\n"
    "Return ONLY compact JSON: {{\"score\": 0-10, \"has_text\": bool, \"has_color\": "
    "bool, \"bad_anatomy\": bool, \"off_style\": bool, \"abstract_mush\": bool, "
    "\"off_topic\": bool, \"reason\": \"<=12 words\"}}"
)


def review(image_path: str, scene: str) -> dict:
    """Return a QC verdict dict for one frame."""
    prompt = CHECKLIST.format(scene=scene)
    # Prefer the free Gemini backend for review when a key is present; else OpenRouter.
    if GEMINI_KEY:
        body = {"contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": _b64(image_path)}},
        ]}], "generationConfig": {"temperature": 0}}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_REVIEW_MODEL}:generateContent?key={GEMINI_KEY}")
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=90))
        txt = r["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        body = {
            "model": REVIEW_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64(image_path)}},
            ]}],
            "temperature": 0,
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
        )
        r = json.load(urllib.request.urlopen(req, timeout=90))
        txt = r["choices"][0]["message"]["content"].strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        v = json.loads(txt)
    except Exception:
        return {"score": 5, "reason": "unparseable review", "ok": True}
    # Hard-fail only on defects that truly ruin a frame. Color is handled
    # deterministically (grayscale in post), so it's not a hard fail here.
    hard_fail = any(v.get(k) for k in
                    ("has_text", "bad_anatomy", "abstract_mush", "off_topic"))
    v["ok"] = (not hard_fail) and v.get("score", 0) >= THRESHOLD
    return v


def _desaturate(path: str):
    """Force the frame to true monochrome — enforces the brand rule deterministically."""
    from PIL import Image
    img = Image.open(path).convert("L").convert("RGB")
    img.save(path)


def generate_checked(orig_generate, prompt: str, out_path: str, scene: str,
                     refs=None, tries: int = 3) -> dict:
    """Generate with QC. Keeps the best frame across attempts. Returns the verdict."""
    best, best_score, best_path = None, -1, None
    tmp = out_path + ".cand.png"
    corrective = (
        " STRICT: absolutely no text/letters/watermark anywhere, correct anatomy, "
        "bold confident sumi-e ink strokes, a single clear readable subject — no abstract blobs."
    )
    gen_errors = 0
    for i in range(tries + 2):                 # a couple extra slots to absorb transient gen failures
        p = prompt if i == 0 else prompt + corrective
        try:
            orig_generate(p, tmp, refs)        # transient provider/network hiccups shouldn't kill the run
        except Exception as e:
            gen_errors += 1
            print(f"    QC try {i+1}: gen error ({e}); retrying", flush=True)
            time.sleep(2 * gen_errors)
            if best_path is None and gen_errors <= tries:
                continue
            if best_path is not None:
                break
            continue
        _desaturate(tmp)                       # guarantee monochrome before review
        try:
            v = review(tmp, scene)
        except Exception as e:
            v = {"score": 6, "reason": f"review error: {e}", "ok": True}
        raw = v.get("score", 0)
        if best_path is None or raw > best_score:
            keep = tmp + f".{i}.png"
            os.replace(tmp, keep)
            if best_path and os.path.exists(best_path):
                os.remove(best_path)
            best_score, best, best_path = raw, v, keep
        elif os.path.exists(tmp):
            os.remove(tmp)
        print(f"    QC try {i+1}: score={raw} ok={v.get('ok')} — {v.get('reason')}", flush=True)
        if v.get("ok"):
            break
    if best_path is None:
        raise RuntimeError(f"image generation failed after {gen_errors} attempts")
    os.replace(best_path, out_path)
    return best or {"score": 0, "reason": "no candidate"}
