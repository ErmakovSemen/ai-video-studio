"""Instagram Reels publisher — Graph API.

Setup (operator): Instagram Business/Creator account linked to a Facebook Page, a
Facebook app with instagram_content_publish permission, a long-lived access token,
and the IG user id. The Graph API fetches the video from a PUBLIC url, so we first
push the clip to a temporary public host (catbox.moe).
"""
import json
import time
import uuid
import urllib.request
from .base import Publisher, VideoMeta
from . import config

GRAPH = "https://graph.facebook.com/v21.0"


def _public_url(path: str) -> str:
    """Upload the file to catbox.moe and return a public URL (multipart)."""
    b = "----b" + uuid.uuid4().hex

    def field(n, v):
        return (f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n').encode()

    body = field("reqtype", "fileupload")
    body += (f'--{b}\r\nContent-Disposition: form-data; name="fileToUpload"; filename="v.mp4"\r\n'
             f'Content-Type: video/mp4\r\n\r\n').encode() + open(path, "rb").read() + b"\r\n"
    body += (f'--{b}--\r\n').encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "https://catbox.moe/user/api.php", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=300)
    return r.read().decode().strip()


def _post(url, params):
    import urllib.parse
    data = urllib.parse.urlencode(params).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=120))


def _get(url):
    return json.load(urllib.request.urlopen(url, timeout=60))


class InstagramPublisher(Publisher):
    name = "instagram"
    label = "Instagram Reels"
    needs = ("access_token", "ig_user_id")
    setup_hint = ("IG Business/Creator + Facebook app (instagram_content_publish), long-lived "
                  "access token + IG user id. See SETUP-INSTAGRAM.md")
    fields = [
        {"key": "access_token", "label": "Long-lived access token", "secret": True},
        {"key": "ig_user_id", "label": "Instagram user id", "secret": False},
    ]

    def __init__(self):
        self.token = config.get("instagram", "access_token", env="IG_ACCESS_TOKEN", default="")
        self.ig_user_id = config.get("instagram", "ig_user_id", env="IG_USER_ID", default="")

    def configured(self) -> bool:
        return bool(self.token and self.ig_user_id)

    def publish(self, video_path: str, meta: VideoMeta) -> dict:
        if not self.configured():
            raise RuntimeError("Instagram not configured: set access_token and ig_user_id")
        caption = meta.title + (("\n\n" + meta.description) if meta.description else "")
        if meta.tags:
            caption += "\n\n" + meta.hashtags()
        url = _public_url(video_path)
        # 1) create media container
        c = _post(f"{GRAPH}/{self.ig_user_id}/media", {
            "media_type": "REELS", "video_url": url, "caption": caption[:2200],
            "access_token": self.token})
        cid = c.get("id")
        if not cid:
            raise RuntimeError(f"ig container failed: {c}")
        # 2) wait until the container finished processing
        for _ in range(30):
            st = _get(f"{GRAPH}/{cid}?fields=status_code&access_token={self.token}")
            if st.get("status_code") == "FINISHED":
                break
            if st.get("status_code") == "ERROR":
                raise RuntimeError(f"ig processing error: {st}")
            time.sleep(5)
        # 3) publish
        pub = _post(f"{GRAPH}/{self.ig_user_id}/media_publish", {
            "creation_id": cid, "access_token": self.token})
        mid = pub.get("id")
        if not mid:
            raise RuntimeError(f"ig publish failed: {pub}")
        return {"platform": "instagram", "id": mid,
                "url": f"https://www.instagram.com/reel/{mid}/"}
