"""TikTok publisher — Content Posting API (direct post).

Setup (operator): create a TikTok developer app (developers.tiktok.com), add the
Content Posting API product, get client_key/client_secret, complete OAuth to obtain
a refresh token (scope: video.publish). Direct posting to public requires the app to
pass TikTok's audit; until then uploads land in the account's inbox/drafts.
"""
import json
import urllib.request
import urllib.parse
from .base import Publisher, VideoMeta
from . import config

OAUTH = "https://open.tiktokapis.com/v2/oauth/token/"
INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"


def _post_json(url, payload, token=None):
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=60))


class TikTokPublisher(Publisher):
    name = "tiktok"
    label = "TikTok"
    needs = ("client_key", "client_secret", "refresh_token")
    setup_hint = ("developers.tiktok.com → app with Content Posting API, scope video.publish. "
                  "See SETUP-TIKTOK.md. Until the app is audited, posts go to drafts.")
    fields = [
        {"key": "client_key", "label": "Client key", "secret": False},
        {"key": "client_secret", "label": "Client secret", "secret": True},
        {"key": "refresh_token", "label": "Refresh token", "secret": True},
        {"key": "privacy", "label": "Privacy (PUBLIC_TO_EVERYONE / SELF_ONLY)", "secret": False},
    ]

    def __init__(self):
        self.client_key = config.get("tiktok", "client_key", env="TIKTOK_CLIENT_KEY", default="")
        self.client_secret = config.get("tiktok", "client_secret", env="TIKTOK_CLIENT_SECRET", default="")
        self.refresh_token = config.get("tiktok", "refresh_token", env="TIKTOK_REFRESH_TOKEN", default="")
        self.privacy = config.get("tiktok", "privacy", default="SELF_ONLY")

    def configured(self) -> bool:
        return bool(self.client_key and self.client_secret and self.refresh_token)

    def _access_token(self) -> str:
        data = urllib.parse.urlencode({
            "client_key": self.client_key, "client_secret": self.client_secret,
            "grant_type": "refresh_token", "refresh_token": self.refresh_token}).encode()
        req = urllib.request.Request(OAUTH, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        if "access_token" not in d:
            raise RuntimeError(f"tiktok oauth failed: {d}")
        return d["access_token"]

    def publish(self, video_path: str, meta: VideoMeta) -> dict:
        if not self.configured():
            raise RuntimeError("TikTok not configured: set client_key/client_secret/refresh_token")
        token = self._access_token()
        size = __import__("os").path.getsize(video_path)
        title = (meta.title + (" " + meta.hashtags() if meta.tags else ""))[:2200]
        init = _post_json(INIT, {
            "post_info": {"title": title, "privacy_level": self.privacy,
                          "disable_comment": False, "disable_stitch": False},
            "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                            "chunk_size": size, "total_chunk_count": 1},
        }, token)
        data = init.get("data", {})
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")
        if not upload_url:
            raise RuntimeError(f"tiktok init failed: {init}")
        body = open(video_path, "rb").read()
        put = urllib.request.Request(upload_url, data=body, method="PUT", headers={
            "Content-Type": "video/mp4", "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size-1}/{size}"})
        urllib.request.urlopen(put, timeout=300)
        return {"platform": "tiktok", "id": publish_id,
                "url": "https://www.tiktok.com/", "privacy": self.privacy,
                "note": "uploaded; check TikTok app/drafts (public requires audited app)"}
