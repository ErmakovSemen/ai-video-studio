"""Telegram publisher — posts a video to a channel/chat via the Bot API."""
import json
import uuid
import urllib.request
from .base import Publisher, VideoMeta
from . import config


class TelegramPublisher(Publisher):
    name = "telegram"
    label = "Telegram"
    needs = ("bot_token", "channel")
    setup_hint = ("Create a bot via @BotFather to get the token, add it as an admin of your "
                  "channel, and set the channel as @username (or a numeric chat id).")
    fields = [
        {"key": "bot_token", "label": "Bot token", "secret": True},
        {"key": "channel", "label": "Channel (@username or chat id)", "secret": False},
    ]

    def __init__(self):
        self.token = config.get("telegram", "bot_token", env="AGT_TG_BOT_TOKEN", default="")
        self.channel = config.get("telegram", "channel", env="TG_CHANNEL", default="@PrometeyApp")

    def configured(self) -> bool:
        return bool(self.token and self.channel)

    def publish(self, video_path: str, meta: VideoMeta) -> dict:
        if not self.configured():
            raise RuntimeError("Telegram not configured: set bot_token and channel")
        caption = meta.title
        if meta.description:
            caption = f"{meta.title}\n\n{meta.description}"
        caption = caption[:1024]
        b = "----b" + uuid.uuid4().hex

        def part(n, v):
            return (f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n').encode()

        body = part("chat_id", self.channel) + part("caption", caption) + part("supports_streaming", "true")
        body += (f'--{b}\r\nContent-Disposition: form-data; name="video"; filename="v.mp4"\r\n'
                 f'Content-Type: video/mp4\r\n\r\n').encode() + open(video_path, "rb").read() + b"\r\n"
        body += (f'--{b}--\r\n').encode()
        r = urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/sendVideo", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=180)
        d = json.load(r)
        if not d.get("ok"):
            raise RuntimeError(f"telegram error: {d}")
        res = d.get("result", {})
        mid = res.get("message_id")
        chan = self.channel.lstrip("@")
        url = f"https://t.me/{chan}/{mid}" if not self.channel.startswith("-") else None
        return {"platform": "telegram", "id": mid, "url": url, "channel": self.channel}
