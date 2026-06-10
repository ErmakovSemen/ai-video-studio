"""Daily autopost orchestrator — fully free (green-lane) render + YouTube upload.

One self-contained process so CI doesn't have to coordinate across steps:
  1. pick the next not-yet-posted scenario from ROTATION;
  2. render it FREE (draft + polish): Ken-Burns on the locked Огонёк canon art +
     word-level karaoke captions via edge-tts — no Gemini, no Kling, zero paid API;
  3. upload to YouTube as a Short, scheduled public via publishAt (now + N hours);
  4. record the slug in scripts/autopost_state.json so it isn't posted again.

Run:
  python -m scripts.autopost_daily                 # next scenario, +18h public
  python -m scripts.autopost_daily --schedule-in 6
  python -m scripts.autopost_daily --dry-run       # render only, no upload
  python -m scripts.autopost_daily --list          # show rotation + what's posted

Env (set by CI from repo Secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import os, sys, json, time, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from studio import story                              # noqa: E402
from publish import registry, VideoMeta               # noqa: E402

QUEUE = os.path.join(ROOT, "queue")
STATE = os.path.join(ROOT, "scripts", "autopost_state.json")

# Ready, locked-canon Огонёк episodes (greece already live on the channel).
ROTATION = ["ognyok_norse", "ognyok_japan", "ognyok_space"]

# Per-episode publish metadata (title/description tuned for Shorts discovery).
META = {
    "ognyok_norse": {
        "title": "Огонь не на одну зиму ❄️🔥 #Shorts",
        "desc": "Один большой костёр не греет всю зиму. Грей очаг — по полену каждый день. "
                "Дисциплина это не рывок, а ровный огонь.",
        "tags": ["мотивация", "дисциплина", "саморазвитие", "привычки", "Прометей"],
    },
    "ognyok_japan": {
        "title": "Кайдзен: 1 маленький шаг 🔥🇯🇵 #Shorts",
        "desc": "Путь — это один маленький шаг каждый день. Кайдзен против выгорания. "
                "Не герой одного рывка, а ровное движение.",
        "tags": ["кайдзен", "мотивация", "дисциплина", "привычки", "Прометей"],
    },
    "ognyok_space": {
        "title": "Топливо понемногу каждый день 🚀🔥 #Shorts",
        "desc": "Один разгон не довезёт до цели. Топливо — понемногу, но каждый день. "
                "Так доходят далеко.",
        "tags": ["мотивация", "цели", "дисциплина", "космос", "Прометей"],
    },
}


def load_state() -> dict:
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"posted": []}


def save_state(st: dict):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def next_slug(st: dict) -> str | None:
    done = set(st.get("posted", []))
    for s in ROTATION:
        if s not in done:
            return s
    return None


def render_free(slug: str) -> str:
    """Render the scenario FREE (draft+polish) -> queue/<slug>.mp4."""
    sc = story.load(os.path.join(ROOT, "scenarios", f"{slug}.json"))
    os.makedirs(QUEUE, exist_ok=True)
    out = os.path.join(QUEUE, f"{slug}.mp4")
    wd = os.path.join(ROOT, "work", f"auto_{slug}_{int(time.time())}")
    print(f"[render] {slug}: draft+polish (free, no paid API) -> {out}")
    story.build(sc, out, wd, base_dir=ROOT, draft=True, polish=True)
    if not os.path.exists(out) or os.path.getsize(out) < 10_000:
        raise RuntimeError(f"render produced no usable file: {out}")
    print(f"[render] ok: {os.path.getsize(out)//1024} KB")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule-in", type=float, default=18,
                    help="hours from now the Short goes public (publishAt)")
    ap.add_argument("--dry-run", action="store_true", help="render only, skip upload")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    st = load_state()
    if a.list:
        done = set(st.get("posted", []))
        for s in ROTATION:
            print(("[posted] " if s in done else "[pending] ") + s)
        return

    slug = next_slug(st)
    if not slug:
        print("rotation exhausted — all scenarios posted. Add more to ROTATION.")
        return

    mp4 = render_free(slug)
    m = META.get(slug, {})

    if a.dry_run:
        print(f"[dry-run] rendered {mp4}; skipping upload")
        return

    pub = registry.get("youtube")
    if not pub.configured():
        sys.exit("youtube not configured: set YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN")

    t = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=a.schedule_in)
    publish_at = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = VideoMeta(title=m.get("title", f"Prometey · {slug}"),
                     description=m.get("desc", ""), tags=m.get("tags", []),
                     privacy="public", publish_at=publish_at)
    print(f"[upload] {slug} -> youtube (publishAt {publish_at})")
    res = pub.publish(mp4, meta)
    print("[upload] POSTED:", json.dumps(res, ensure_ascii=False))

    st.setdefault("posted", []).append(slug)
    st["last"] = {"slug": slug, "at": datetime.datetime.now().isoformat(),
                  "result": res, "publish_at": publish_at}
    save_state(st)
    print(f"[state] recorded {slug} as posted ({len(st['posted'])}/{len(ROTATION)})")


if __name__ == "__main__":
    main()
