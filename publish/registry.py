"""Registry of publishers. Add a platform here and the UI/API picks it up."""
from .youtube import YouTubePublisher

_CLASSES = [YouTubePublisher]
# Future: TikTokPublisher, InstagramPublisher, TelegramPublisher …


def publishers() -> list:
    return [cls() for cls in _CLASSES]


def get(name: str):
    for p in publishers():
        if p.name == name:
            return p
    raise KeyError(f"unknown publisher: {name}")


def status() -> list[dict]:
    """For the UI: which platforms exist and whether they're ready to post."""
    out = []
    for p in publishers():
        out.append({"name": p.name, "label": p.label,
                    "configured": p.configured(), "needs": list(p.needs)})
    return out
