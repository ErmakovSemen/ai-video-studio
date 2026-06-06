"""YouTube publisher — uploads via the official YouTube Data API v3 (resumable).

Auth model (no passwords ever touch this code):
  - The operator creates an OAuth client in Google Cloud (Desktop app) and runs
    `python -m publish.youtube_auth` ONCE locally to grant consent in the browser.
    That mints a long-lived refresh token.
  - Set env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
  - The server then mints short-lived access tokens from the refresh token — no
    browser, no interaction — and uploads.

Note: until Google audits a new OAuth app, videos uploaded via the API are forced
to `private`. You can still upload automatically and flip them public by hand, or
request an audit. See SETUP-YOUTUBE.md.
"""
import os
from .base import Publisher, VideoMeta

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubePublisher(Publisher):
    name = "youtube"
    label = "YouTube Shorts"
    needs = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")

    def __init__(self):
        self.client_id = os.getenv("YT_CLIENT_ID", "")
        self.client_secret = os.getenv("YT_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("YT_REFRESH_TOKEN", "")

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def _service(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(
            token=None, refresh_token=self.refresh_token, token_uri=TOKEN_URI,
            client_id=self.client_id, client_secret=self.client_secret, scopes=SCOPES)
        return build("youtube", "v3", credentials=creds, cache_discovery=False)

    def publish(self, video_path: str, meta: VideoMeta) -> dict:
        if not self.configured():
            raise RuntimeError("YouTube not configured: set YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN")
        from googleapiclient.http import MediaFileUpload
        yt = self._service()
        # #Shorts in the description/title helps YouTube classify vertical <60s clips
        desc = (meta.description or "").strip()
        if "#shorts" not in desc.lower():
            desc = (desc + "\n\n#Shorts " + meta.hashtags()).strip()
        status = {"privacyStatus": meta.privacy,
                  "selfDeclaredMadeForKids": meta.made_for_kids}
        # Native scheduled publishing: video stays private until publish_at, then goes public.
        publish_at = getattr(meta, "publish_at", None)
        if publish_at:
            status["privacyStatus"] = "private"
            status["publishAt"] = publish_at        # ISO-8601 UTC, e.g. 2026-06-07T09:00:00Z
        body = {
            "snippet": {"title": meta.title[:100], "description": desc[:4900],
                        "tags": meta.tags, "categoryId": meta.category_id},
            "status": status,
        }
        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=-1)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _status, resp = req.next_chunk()
        vid = resp["id"]
        return {"platform": "youtube", "id": vid,
                "url": f"https://youtu.be/{vid}", "privacy": meta.privacy}
