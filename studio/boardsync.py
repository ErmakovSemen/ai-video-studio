"""Cloud board-sync — make the kanban board durable in GitHub so the live page and the
agent share one source of truth.

The page runs on an ephemeral host (Render): its content.json is lost on restart and is
invisible to an agent running elsewhere. We mirror the board to the GitHub repo:
  - page GET  → pull() latest <name>.json from GitHub (so it shows agent results)
  - page POST → push() the board back to GitHub (so the agent sees "Отдать Claude")
  - a GitHub Action runs `studio_ctl claim`, processes the column, commits results back.

Best-effort: every call degrades to the local disk copy if GitHub creds/network absent.
Env: GH_TOKEN (repo-write PAT), GH_REPO ("owner/repo"), optional GH_BRANCH (default main).
"""
import os, json, base64, urllib.request

REPO = os.getenv("GH_REPO", "ErmakovSemen/ai-video-studio")
BRANCH = os.getenv("GH_BRANCH", "master")
TOKEN = os.getenv("GH_TOKEN", "")
API = "https://api.github.com"


def enabled() -> bool:
    return bool(TOKEN and REPO)


def _req(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "Content-Type": "application/json", "User-Agent": "prometey-boardsync"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def default_board(name: str) -> dict:
    """Standard 6-column content pipeline board (matches the app's auto-init)."""
    return {"title": name, "columns": [
        {"id": "ideas",      "name": "💡 Идеи",             "cards": []},
        {"id": "draft",      "name": "✏️ Черновик",          "cards": []},
        {"id": "montage",    "name": "🎬 Монтаж",            "cards": []},
        {"id": "review",     "name": "🔍 Ревью",              "cards": []},
        {"id": "await_post", "name": "📤 Ожидание постинга",  "cards": []},
        {"id": "posted",     "name": "✅ Опубликовано",       "cards": []},
    ]}


def add_card(name: str, column_id: str, card: dict,
             message: str = "board: add card from CLI") -> bool:
    """Pull the board (or init default), upsert `card` into `column_id`, push back.
    Upsert is by card['id'] so re-runs update instead of duplicating. Best-effort."""
    board = pull(name) or default_board(name)
    cols = board.get("columns") or default_board(name)["columns"]
    board["columns"] = cols
    col = next((c for c in cols if c.get("id") == column_id), None)
    if col is None:
        col = {"id": column_id, "name": column_id, "cards": []}
        cols.append(col)
    col.setdefault("cards", [])
    cid = card.get("id")
    existing = next((c for c in col["cards"] if c.get("id") == cid), None)
    if existing:
        existing.update(card)
    else:
        col["cards"].append(card)
    return push(name, board, message=message)


def pull(name: str) -> dict | None:
    """Fetch <name>.json from the repo (raw). Returns dict or None on any failure."""
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{name}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "prometey-boardsync"})
        return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    except Exception:
        return None


def push(name: str, data: dict, message: str = "board: update from page") -> bool:
    """Commit <name>.json to the repo via the contents API. Best-effort -> bool."""
    if not enabled():
        return False
    path = f"{name}.json"
    try:
        sha = None
        try:
            cur = _req(f"{API}/repos/{REPO}/contents/{path}?ref={BRANCH}")
            sha = cur.get("sha")
        except Exception:
            pass
        content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
        body = {"message": f"{message} [skip ci]", "content": content, "branch": BRANCH}
        if sha:
            body["sha"] = sha
        _req(f"{API}/repos/{REPO}/contents/{path}", method="PUT", body=body)
        return True
    except Exception:
        return False
