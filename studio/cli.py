"""Content factory CLI.

Usage:
  python -m studio.cli render scenarios/icarus.json [--out outputs/icarus.mp4]
  python -m studio.cli image "a prometheus mascot ..." --out out.png [--ref a.png]
"""
import argparse, os, sys, json, time
from studio import story, imagegen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cmd_render(args):
    sc = story.load(args.scenario)
    out = args.out or os.path.join(ROOT, "outputs", f"{os.path.splitext(os.path.basename(args.scenario))[0]}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wd = os.path.join(ROOT, "work", f"job_{int(time.time())}")
    print(f"rendering '{sc.get('title')}' -> {out}")
    log = story.build(sc, out, wd, base_dir=ROOT)
    print(json.dumps(log, ensure_ascii=False, indent=2))
    # Sync a card onto the project board so CLI work shows up on the Kanban.
    # Best-effort: needs GH_TOKEN; degrades silently otherwise.
    try:
        from studio import boardsync
        key = os.path.splitext(os.path.basename(args.scenario))[0]
        project = sc.get("project") or "chayniy"
        ok = boardsync.add_card(f"{project}_content", "review", {
            "id": f"cli_{key}",
            "title": sc.get("title", key),
            "desc": f"Отрендерено через CLI · {os.path.basename(out)}",
            "video": f"/outputs/{os.path.basename(out)}",
            "scenario": args.scenario,
            "tags": ["rendered", "cli"],
        }, message=f"board: rendered {key}")
        print(f"board sync: {'ok' if ok else 'skipped (set GH_TOKEN)'}")
    except Exception as e:
        print(f"board sync: error {e}")


def cmd_image(args):
    imagegen.generate_image(args.prompt, args.out, args.ref or [])
    print("saved", args.out)


def main():
    p = argparse.ArgumentParser(prog="studio")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render"); r.add_argument("scenario"); r.add_argument("--out")
    r.set_defaults(func=cmd_render)
    im = sub.add_parser("image"); im.add_argument("prompt"); im.add_argument("--out", required=True)
    im.add_argument("--ref", action="append"); im.set_defaults(func=cmd_image)
    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
