"""Durable artifact host — push a local file to a public URL and pull it back.

On free tiers (/outputs, media/uploads) artifacts are ephemeral and not in git, so an
agent running elsewhere can't reach a video the web page just produced. We bridge that by
mirroring artifacts to catbox.moe: render/montage → catbox URL stored on the card → the
agent fetches by URL, edits, uploads the result back. Same mechanism the IG publisher uses.
"""
import os
import uuid
import urllib.request

CATBOX = "https://catbox.moe/user/api.php"


def upload(path: str, filename: str | None = None) -> str:
    """Upload a local file to catbox.moe; return its public URL. Raises on failure."""
    fn = filename or os.path.basename(path)
    ctype = "video/mp4" if fn.lower().endswith((".mp4", ".mov", ".webm")) else "application/octet-stream"
    b = "----b" + uuid.uuid4().hex

    def field(n, v):
        return (f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n').encode()

    body = field("reqtype", "fileupload")
    body += (f'--{b}\r\nContent-Disposition: form-data; name="fileToUpload"; filename="{fn}"\r\n'
             f'Content-Type: {ctype}\r\n\r\n').encode() + open(path, "rb").read() + b"\r\n"
    body += (f'--{b}--\r\n').encode()
    req = urllib.request.Request(CATBOX, data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    url = urllib.request.urlopen(req, timeout=300).read().decode().strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox upload failed: {url[:200]}")
    return url


def upload_best_effort(path: str, filename: str | None = None) -> str | None:
    """Upload but never raise — returns the URL or None. For non-critical mirroring."""
    try:
        return upload(path, filename)
    except Exception:
        return None


def fetch(url: str, out_path: str) -> str:
    """Download a remote artifact to out_path (so the agent can edit a page-made file)."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (prometey-studio)"})
    with urllib.request.urlopen(req, timeout=300) as r, open(out_path, "wb") as f:
        f.write(r.read())
    return out_path
