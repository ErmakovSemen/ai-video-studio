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
