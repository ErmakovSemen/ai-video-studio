"""Bake per-scene illustration stills for a scenario, ONCE, and commit them.

Why: the free CI render (draft+polish) otherwise pans the bare mascot PNG on a
flat background — empty, monotone. Greece-level quality comes from a distinct
composed illustration per scene (environment + characters). We generate those via
cheap Gemini ONCE locally (green-lane: cheap previews), commit them to
assets/scenes/<slug>/scene{i}.png, and then every CI render is FREE and rich.

Run (needs OPENROUTER_API_KEY in env, e.g. `set -a; . ../venture-agt/.secrets.env`):
  python -m scripts.bake_stills ognyok_norse
  python -m scripts.bake_stills ognyok_norse --force   # re-bake existing
"""
import os, sys, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from studio import story, imagegen          # noqa: E402

NO_TEXT = (" IMPORTANT: absolutely NO text, NO letters, NO words, NO captions, NO writing, "
           "NO watermark, NO signs anywhere in the image — clean illustration only. "
           "Full-bleed vertical 9:16 composition, fill the whole frame, no empty flat margins.")


def bake(slug: str, force: bool = False):
    sc = story.load(os.path.join(ROOT, "scenarios", f"{slug}.json"))
    chars = {k: os.path.join(ROOT, v) for k, v in sc.get("characters", {}).items()}
    style = sc.get("style", "")
    out_dir = os.path.join(ROOT, "assets", "scenes", slug)
    os.makedirs(out_dir, exist_ok=True)
    n = len(sc["scenes"])
    for i, scene in enumerate(sc["scenes"]):
        out = os.path.join(out_dir, f"scene{i}.png")
        if os.path.exists(out) and not force:
            print(f"[skip] scene{i} exists")
            continue
        refs = [chars[name] for name in scene.get("refs", []) if name in chars]
        prompt = f"{style} SCENE: {scene['image']}{NO_TEXT}"
        print(f"[bake] {slug} scene{i+1}/{n} (refs: {len(refs)}) -> {out}")
        imagegen.generate_image(prompt, out, refs)
    print(f"[done] {slug}: stills in {out_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="scenario slug, e.g. ognyok_norse")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if not os.getenv("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY required (set -a; . ../venture-agt/.secrets.env)")
    bake(a.slug, a.force)


if __name__ == "__main__":
    main()
