"""Загрузка ролика на YouTube через publish.youtube (YouTube Data API v3).
Нужны env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (см. SETUP-YOUTUBE.md).
Запуск из корня репо: python3 -m animations.jinjunmei.upload_youtube [--theme ink|kraft] [--privacy public|unlisted|private]"""
import argparse, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from publish.base import VideoMeta  # noqa: E402
from publish.youtube import YouTubePublisher  # noqa: E402

TITLE = "Цзинь Цзюнь Мэй: как родился «золотой» чай · карандашный мульт"
DESCRIPTION = """Горы Уишань, деревня Тунму — родина первого красного чая.
В 2005 году здесь сделали Цзинь Цзюнь Мэй (金骏眉) — чай только из почек: около 50 000 почек на 500 г.
金 — золото, 骏 — горы, 眉 — бровь. «Золотые брови Уишаня».

Мульт нарисован кодом: каждая линия карандаша — JavaScript."""
TAGS = ["Цзинь Цзюнь Мэй", "金骏眉", "Jin Jun Mei", "красный чай", "китайский чай", "Уишань", "чай", "история чая", "анимация"]

ap = argparse.ArgumentParser()
ap.add_argument("--theme", default="ink", choices=["ink", "kraft"])
ap.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
a = ap.parse_args()
video = pathlib.Path(__file__).parent / "out" / f"jinjunmei_{a.theme}.mp4"
pub = YouTubePublisher()
if not pub.configured():
    sys.exit("YouTube не настроен: нужны YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN")
res = pub.publish(str(video), VideoMeta(title=TITLE, description=DESCRIPTION, tags=TAGS, privacy=a.privacy, category_id="1"))
print(res)
