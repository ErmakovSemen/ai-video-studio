"""Публикация готового ролика в соцсети одной командой (используется workflow «Publish video»).

python -m scripts.publish_video --project animations/teahistory --platforms youtube,telegram [--privacy unlisted]
Видео: <project>/out/<name>.mp4 (из youtube.json → video, либо единственный mp4 в out/).
Заголовок/описание/теги — из <project>/youtube.json. Результат — JSON в stdout.
"""
import argparse, glob, json, os, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from publish import registry
from publish.base import VideoMeta

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--platforms", default="youtube")
ap.add_argument("--privacy", default=None, help="public | unlisted | private (по умолчанию из youtube.json)")
a = ap.parse_args()

meta_path = os.path.join(a.project, "youtube.json")
m = json.load(open(meta_path, encoding="utf-8"))
video = None
if m.get("video"):
    rel = urllib.parse.urlparse(m["video"]).path.split("/master/", 1)[-1]
    if os.path.exists(rel):
        video = rel
if not video:
    mp4 = sorted(glob.glob(os.path.join(a.project, "out", "*.mp4")))
    video = mp4[0] if len(mp4) == 1 else None
if not video:
    sys.exit(f"не нашёл видео для {a.project}")

desc = m.get("description", "")
meta = VideoMeta(title=m["title"], description="\n".join(desc) if isinstance(desc, list) else desc,
                 tags=m.get("tags", []), privacy=a.privacy or m.get("privacy_first_upload", "unlisted"))
out, failed = [], False
for name in [p.strip() for p in a.platforms.split(",") if p.strip()]:
    pub = registry.get(name)
    if not pub.configured():
        out.append({"platform": name, "error": "не настроены ключи"}); failed = True; continue
    try:
        out.append(pub.publish(video, meta))
    except Exception as e:  # noqa: BLE001
        out.append({"platform": name, "error": str(e)[:500]}); failed = True
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(1 if failed else 0)
