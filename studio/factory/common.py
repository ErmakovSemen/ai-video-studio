"""Общее для агентов фабрики: LLM-вызов, доступ к проекту/доске, состояние на диске."""
import os, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
STATE_DIR = OUT / "factory_state"          # durable (bind-mounted), переживает redeploy
STATE_DIR.mkdir(parents=True, exist_ok=True)

OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
TEXT_MODEL = os.getenv("FACTORY_TEXT_MODEL", "anthropic/claude-sonnet-4.5")


def call_llm(system: str, user: str, model: str = None, temperature: float = 0.6, timeout: int = 90) -> str:
    if not OR_KEY:
        raise RuntimeError("OPENROUTER_API_KEY не задан")
    body = {"model": model or TEXT_MODEL, "temperature": temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    return r["choices"][0]["message"]["content"].strip()


def parse_json(txt: str):
    if "```" in txt:
        txt = txt.split("```")[1]
        if txt.lstrip().startswith("json"):
            txt = txt.lstrip()[4:]
    txt = txt.strip()
    for a, b in (("{", "}"), ("[", "]")):
        if txt.startswith(a):
            end = txt.rfind(b)
            return json.loads(txt[:end + 1])
    start = min((i for i in (txt.find("{"), txt.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError("no json in response")
    end = max(txt.rfind("}"), txt.rfind("]"))
    return json.loads(txt[start:end + 1])


def load_project(slug: str) -> dict:
    return json.loads((ROOT / "projects" / slug / "project.json").read_text(encoding="utf-8"))


def get_board(project: dict) -> dict:
    from studio import boardsync
    name = project["board"]
    return boardsync.pull(name) or boardsync.default_board(name)


def save_board(project: dict, board: dict, message: str) -> bool:
    from studio import boardsync
    return boardsync.push(project["board"], board, message=message)


def col(board: dict, col_id: str) -> dict:
    c = next((x for x in board["columns"] if x["id"] == col_id), None)
    if c is None:
        c = {"id": col_id, "name": col_id, "cards": []}
        board["columns"].append(c)
    c.setdefault("cards", [])
    return c


def move_card(board: dict, card: dict, from_id: str, to_id: str):
    col(board, from_id)["cards"] = [c for c in col(board, from_id)["cards"] if c.get("id") != card.get("id")]
    col(board, to_id)["cards"].append(card)


ACTIVITY_LOG = STATE_DIR / "activity.log"


def log(role: str, msg: str):
    line = f"[factory:{role}] {msg}"
    print(line, flush=True)
    try:                                    # durable tail for the dashboard
        import time as _t
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(f"{int(_t.time())}|{role}|{msg}\n")
        # keep the file bounded
        if ACTIVITY_LOG.stat().st_size > 200_000:
            lines = ACTIVITY_LOG.read_text(encoding="utf-8").splitlines()[-400:]
            ACTIVITY_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def autonomous_on() -> bool:
    return bool(read_state("autonomous.json", {}).get("on"))


def set_autonomous(on: bool):
    write_state("autonomous.json", {"on": bool(on), "changed": __import__("time").time()})


def state_path(name: str) -> Path:
    return STATE_DIR / name


def read_state(name: str, default=None):
    p = state_path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_state(name: str, data):
    state_path(name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
