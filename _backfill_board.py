"""Backfill the chayniy_content board 'posted' column with already-published videos."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from studio import boardsync

PUBLISHED = [
    ("calm_focus",   "Почему чай успокаивает, но не усыпляет", "https://youtu.be/WCyew_o9eyA", True),
    ("samurai_tea",  "Этот чай пили самураи перед боем",       "https://youtu.be/x66EogU3sAE", True),
    ("bitter_tea",   "Почему чай горчит — и как это исправить", "https://youtu.be/ZshOhYpswyo", True),
    ("golden_tea",   "Чай, который дороже золота",             "https://youtu.be/eJ636uk9DFE", False),
    ("milk_tea",     "Почему англичане льют молоко в чай",      "https://youtu.be/tYJx8WF7RtA", True),
    ("caffeine_myth","В чае больше кофеина, чем в кофе?",       "https://youtu.be/SNFJLr8Qdo8", True),
]

print("boardsync enabled:", boardsync.enabled())
# build the whole board once, then push (cheaper than 6 pulls/pushes)
board = boardsync.pull("chayniy_content") or boardsync.default_board("chayniy_content")
posted = next(c for c in board["columns"] if c["id"] == "posted")
posted.setdefault("cards", [])
for key, title, url, caps in PUBLISHED:
    cid = f"cli_{key}"
    card = {"id": cid, "title": title,
            "desc": f"{url}\nсубтитры: {'да' if caps else 'нет'}",
            "video": url, "scenario": f"scenarios/chayniy/{key}.json",
            "tags": ["published", "cli", "youtube"]}
    ex = next((c for c in posted["cards"] if c.get("id") == cid), None)
    if ex:
        ex.update(card)
    else:
        posted["cards"].append(card)
ok = boardsync.push("chayniy_content", board, message="board: backfill published shorts")
print("pushed:", ok, "| posted cards:", len(posted["cards"]))
