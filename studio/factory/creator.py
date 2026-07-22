"""Агент-креатор: придумывает новую идею ролика и кладёт карточку в колонку "Идеи"."""
import time
from studio.factory import common as C
from studio import scenegen

MIN_IDEAS = 2          # если в очереди идей >= этого числа — не генерим новую


def _used_topics(project: dict, board: dict) -> str:
    titles = []
    for c in board.get("columns", []):
        for card in c.get("cards", []):
            t = card.get("title")
            if t:
                titles.append(t)
    sdir = C.ROOT / "scenarios" / project.get("scenarios_dir", project["id"])
    if sdir.is_dir():
        for f in sdir.glob("*.json"):
            titles.append(f.stem)
    return "\n".join(f"- {t}" for t in titles[-60:]) or "(пока нет)"


def maybe_create_idea(project: dict, board: dict) -> bool:
    ideas = C.col(board, "ideas")["cards"]
    if len(ideas) >= MIN_IDEAS:
        C.log("creator", f"в очереди уже {len(ideas)} идей, пропускаю")
        return False

    ipath = C.STATE_DIR / f"insights_{project['id']}.md"
    insights = ipath.read_text(encoding="utf-8") if ipath.exists() else ""
    idea = "Придумай новую идею для ролика." + (f" Учти выводы из аналитики: {insights}" if insights else "")

    res = scenegen.generate(idea, project, avoid_topics=_used_topics(project, board))
    slug = res["slug"]
    card = {
        "id": f"idea_{slug}_{int(time.time())}", "title": res["title"], "desc": res.get("hook", ""),
        "scenario": res["scenario"], "yt_desc": res.get("desc", ""), "yt_tags": res.get("tags", []),
        "tags": ["auto", "creator"], "created": int(time.time()), "retries": 0,
    }
    ideas.append(card)
    ok = C.save_board(project, board, message=f"factory: new idea {slug}")
    C.log("creator", f"новая идея '{res['title']}' -> board {'ok' if ok else 'FAILED PUSH'}")
    return True
