"""Auto-poster: post the next queued video to a platform (one per cadence tick).

Queue layout (drop a video + its metadata here to schedule it):
  queue/<slug>.mp4      the video
  queue/<slug>.json     {"title","description","tags":[...],"privacy","publish_at"}

Run (e.g. daily via a scheduled task):
  python -m publish.autopost --platform youtube
  python -m publish.autopost --platform youtube --schedule-in 18   # go public in 18h

Posts the OLDEST pending item, then moves both files to queue/posted/.
Env (YT_CLIENT_ID/SECRET/REFRESH_TOKEN) must be set, e.g. `set -a; . .secrets.env`.
"""
import os, sys, json, glob, argparse, datetime, shutil
from publish import registry, VideoMeta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue")
DONE = os.path.join(QUEUE, "posted")


def pending() -> list[str]:
    os.makedirs(QUEUE, exist_ok=True)
    return sorted(p for p in glob.glob(os.path.join(QUEUE, "*.mp4")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="youtube")
    ap.add_argument("--schedule-in", type=float, default=0,
                    help="hours from now to auto-publish (0 = use item's privacy immediately)")
    ap.add_argument("--list", action="store_true", help="just list the queue")
    a = ap.parse_args()

    items = pending()
    if a.list:
        print(f"{len(items)} pending:", *[os.path.basename(p) for p in items], sep="\n  ")
        return
    if not items:
        print("queue empty — nothing to post")
        return

    mp4 = items[0]
    meta_path = os.path.splitext(mp4)[0] + ".json"
    m = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}

    pub = registry.get(a.platform)
    if not pub.configured():
        sys.exit(f"{a.platform} not configured (missing: {', '.join(pub.needs)})")

    publish_at = m.get("publish_at")
    if a.schedule_in > 0:
        t = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=a.schedule_in)
        publish_at = t.strftime("%Y-%m-%dT%H:%M:%SZ")

    meta = VideoMeta(title=m.get("title", "Prometey"), description=m.get("description", ""),
                     tags=m.get("tags", []), privacy=m.get("privacy", "public"),
                     publish_at=publish_at)
    print(f"posting {os.path.basename(mp4)} -> {a.platform}"
          + (f" (publishAt {publish_at})" if publish_at else ""))
    res = pub.publish(mp4, meta)
    print("POSTED:", res)

    os.makedirs(DONE, exist_ok=True)
    shutil.move(mp4, os.path.join(DONE, os.path.basename(mp4)))
    if os.path.exists(meta_path):
        shutil.move(meta_path, os.path.join(DONE, os.path.basename(meta_path)))
    with open(os.path.join(DONE, "log.txt"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now().isoformat()} {json.dumps(res, ensure_ascii=False)}\n")


if __name__ == "__main__":
    main()
