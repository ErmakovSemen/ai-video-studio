"""studio_ctl — drive the content pipeline from the terminal, same code as the web page.

The web buttons and this CLI operate on the SAME content.json cards and the SAME studio
modules (story / ai_montage / ai_edit / publish). Artifacts are mirrored to a durable host
(catbox) so a card produced on the cloud page is reachable here by URL, and vice-versa.

Commands:
  list                          show every card by column
  get <card_id>                 print a card as JSON
  render <card_id>              render the card's scenario FREE (draft+polish, baked
                                stills + music if present) -> catbox URL on the card -> Review
  montage <card_id> [-p TEXT]   AI-montage from the card's assets (local paths or URLs)
                                -> catbox URL on the card -> Review
  edit <card_id>                AI caption pass (ai_edit) on the card's scenario
  claim                         process every card in the "🤖 Отдать Claude" column by type
                                (scenario→render, assets→montage), write results back
  publish <card_id> [--to ...]  publish the card's video to configured platforms

Card state lives in content.json (the shared board). Run from the repo root.
"""
import os, sys, json, time, uuid, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from studio import story, host                       # noqa: E402

CONTENT = os.path.join(ROOT, "content.json")
OUT = os.path.join(ROOT, "outputs")
WORK = os.path.join(ROOT, "work")
SCEN = os.path.join(ROOT, "scenarios")
MUSIC = os.path.join(ROOT, "assets", "music", "inspired.mp3")
CLAUDE_COL = "claude"          # handshake column id
REVIEW_COL = "review"


# ---------- board helpers ----------
def load_board() -> dict:
    return json.load(open(CONTENT, encoding="utf-8"))


def save_board(b: dict):
    json.dump(b, open(CONTENT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def find_card(b: dict, cid: str):
    for col in b["columns"]:
        for c in col["cards"]:
            if c.get("id") == cid:
                return c, col
    return None, None


def move_card(b: dict, cid: str, to_col: str):
    c, col = find_card(b, cid)
    if not c:
        return
    col["cards"] = [x for x in col["cards"] if x.get("id") != cid]
    dest = next((k for k in b["columns"] if k["id"] == to_col), None)
    if dest is not None:
        dest["cards"].append(c)


# ---------- asset resolution (local path OR durable URL) ----------
def resolve_asset(a) -> str | None:
    """a may be a str (path/url) or {path,url}. Return a local file path or None."""
    if isinstance(a, dict):
        url, path = a.get("url"), a.get("path")
    elif isinstance(a, str) and a.startswith("http"):
        url, path = a, None
    else:
        url, path = None, a
    if path:
        for cand in (path, os.path.join(ROOT, path.lstrip("/")),
                     os.path.join(ROOT, "media", path.replace("/media/", "", 1).lstrip("/"))):
            if os.path.exists(cand):
                return cand
    if url:
        ext = os.path.splitext(url)[1] or ".bin"
        dst = os.path.join(WORK, "fetched", uuid.uuid4().hex[:10] + ext)
        try:
            return host.fetch(url, dst)
        except Exception as e:
            print(f"  ! fetch failed {url}: {e}")
    return None


# ---------- actions ----------
def do_render(b: dict, cid: str) -> bool:
    c, _ = find_card(b, cid)
    if not c or not c.get("scenario"):
        print(f"  ! {cid}: no scenario to render"); return False
    slug = c["scenario"]
    sc = story.load(os.path.join(SCEN, f"{slug}.json"))
    sdir = os.path.join(ROOT, "assets", "scenes", slug)
    has_baked = os.path.isdir(sdir) and any(f.startswith("scene") for f in os.listdir(sdir))
    music = MUSIC if os.path.exists(MUSIC) else None
    out = os.path.join(OUT, f"card_{cid}.mp4")
    os.makedirs(OUT, exist_ok=True)
    print(f"  render {slug} (baked={has_baked}, music={'y' if music else 'n'})")
    story.build(sc, out, os.path.join(WORK, f"ctl_{cid}_{int(time.time())}"),
                base_dir=ROOT, draft=True, polish=True,
                stills_dir=sdir if has_baked else None, music=music)
    url = host.upload(out, filename=f"{slug}.mp4")
    c["video"] = url; c["video_local"] = f"/outputs/card_{cid}.mp4"
    c.setdefault("tags", []); ("ai-rendered" in c["tags"]) or c["tags"].append("ai-rendered")
    print(f"  -> {url}")
    return True


def do_montage(b: dict, cid: str, prompt: str | None) -> bool:
    from studio import ai_montage
    c, _ = find_card(b, cid)
    if not c:
        print(f"  ! {cid}: not found"); return False
    raw = [resolve_asset(a) for a in c.get("assets", [])]
    fs = [p for p in raw if p]
    if not fs:
        print(f"  ! {cid}: no resolvable assets"); return False
    p = prompt or c.get("montage_prompt") or "Собери динамичный вертикальный ролик 9:16 с сильным хуком."
    out = os.path.join(OUT, f"card_{cid}.mp4")
    os.makedirs(OUT, exist_ok=True)
    print(f"  montage {len(fs)} assets | prompt: {p[:60]}")
    res = ai_montage.ai_montage(fs, p, out, os.path.join(WORK, f"ctlm_{cid}_{int(time.time())}"))
    url = host.upload(out, filename=f"montage_{cid}.mp4")
    c["video"] = url; c["video_local"] = f"/outputs/card_{cid}.mp4"
    c.setdefault("tags", []); ("ai-montage" in c["tags"]) or c["tags"].append("ai-montage")
    print(f"  -> {url} ({res['segments']} segments, {res['duration']}s)")
    return True


def do_edit(b: dict, cid: str) -> bool:
    from studio import ai_editor
    c, _ = find_card(b, cid)
    if not c or not c.get("scenario"):
        print(f"  ! {cid}: no scenario to edit"); return False
    path = os.path.join(SCEN, f"{c['scenario']}.json")
    ai_editor.ai_edit(path)
    c.setdefault("tags", []); ("ai-edited" in c["tags"]) or c["tags"].append("ai-edited")
    print(f"  edited captions for {c['scenario']}")
    return True


def cmd_claim(b: dict):
    col = next((k for k in b["columns"] if k["id"] == CLAUDE_COL), None)
    if not col or not col["cards"]:
        print("nothing handed to Claude (column empty/missing)"); return
    ids = [c["id"] for c in list(col["cards"])]
    print(f"claiming {len(ids)} card(s): {', '.join(ids)}")
    for cid in ids:
        c, _ = find_card(b, cid)
        print(f"- {cid}: {c.get('title','')}")
        ok = do_montage(b, cid, None) if c.get("assets") else do_render(b, cid)
        if ok:
            c["notes"] = (c.get("notes", "") + f"\n🤖 Готово {time.strftime('%Y-%m-%d %H:%M')}").strip()
            move_card(b, cid, REVIEW_COL)
            print(f"  moved -> {REVIEW_COL}")


def main():
    ap = argparse.ArgumentParser(prog="studio_ctl")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    g = sub.add_parser("get"); g.add_argument("card_id")
    r = sub.add_parser("render"); r.add_argument("card_id")
    m = sub.add_parser("montage"); m.add_argument("card_id"); m.add_argument("-p", "--prompt")
    e = sub.add_parser("edit"); e.add_argument("card_id")
    sub.add_parser("claim")
    pu = sub.add_parser("publish"); pu.add_argument("card_id")
    a = ap.parse_args()

    b = load_board()
    if a.cmd == "list":
        for col in b["columns"]:
            print(f"\n[{col['id']}] {col['name']}")
            for c in col["cards"]:
                print(f"  {c['id']:24} {c.get('title','')}")
        return
    if a.cmd == "get":
        c, _ = find_card(b, a.card_id)
        print(json.dumps(c, ensure_ascii=False, indent=2) if c else "not found")
        return
    if a.cmd == "render":
        if do_render(b, a.card_id): move_card(b, a.card_id, REVIEW_COL); save_board(b)
        return
    if a.cmd == "montage":
        if do_montage(b, a.card_id, a.prompt): move_card(b, a.card_id, REVIEW_COL); save_board(b)
        return
    if a.cmd == "edit":
        if do_edit(b, a.card_id): save_board(b)
        return
    if a.cmd == "claim":
        cmd_claim(b); save_board(b)
        return
    if a.cmd == "publish":
        c, _ = find_card(b, a.card_id)
        if not c or not c.get("video"):
            print("no video on card"); return
        print(f"publish wiring: card {a.card_id} video={c['video']} "
              f"(use /api/publish_file or publish.registry)")
        return


if __name__ == "__main__":
    main()
