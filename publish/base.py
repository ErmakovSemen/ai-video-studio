"""Publisher abstraction shared by every platform (YouTube, TikTok, IG, Telegram…)."""
from dataclasses import dataclass, field


@dataclass
class VideoMeta:
    """Platform-agnostic metadata for one upload."""
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    privacy: str = "public"          # public | unlisted | private
    category_id: str = "22"          # YouTube: 22 = People & Blogs
    made_for_kids: bool = False
    publish_at: str | None = None    # ISO-8601 UTC -> native scheduled publishing

    def hashtags(self) -> str:
        return " ".join(f"#{t.lstrip('#')}" for t in self.tags)


class Publisher:
    """Base class. Subclasses implement configured() and publish()."""
    name = "base"
    label = "Base"
    # what the operator must set up before this platform works
    needs = ()
    # settings-UI form spec: list of {key, label, secret, hint}
    fields: list = []
    # short note shown in the Settings UI (e.g. how to get the credentials)
    setup_hint = ""

    def configured(self) -> bool:
        """True when all required credentials are present."""
        raise NotImplementedError

    def publish(self, video_path: str, meta: VideoMeta) -> dict:
        """Upload one video. Returns {platform, id, url, ...}. Raises on failure."""
        raise NotImplementedError
