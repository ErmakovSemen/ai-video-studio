"""Единый таймлайн дневника: страницы и момент появления каждого элемента.
Картинка (timeline.js) берёт время по id, звук (audio.py) — по виду элемента (kind)."""
import json, pathlib

# страница: (id, длительность, [(элемент, вид, время от начала страницы)])
# виды: tape, sticker, drop (полароид), sticky, stamp, write (рука пишет), mark (маркер/стрелка), burst
PAGES = [
    ("cover", 5.0, [("tape", "tape", 0.2), ("title", "write", 0.5), ("koi", "sticker", 1.9), ("note", "sticky", 2.6), ("stamp", "stamp", 3.3)]),
    ("river", 6.0, [("photo", "drop", 0.3), ("tape1", "tape", 0.75), ("tape2", "tape", 0.95), ("text", "write", 1.3), ("arrow", "mark", 3.0), ("badge", "sticker", 3.7)]),
    ("falls", 5.5, [("photo", "drop", 0.3), ("tape1", "tape", 0.75), ("text", "write", 1.1), ("hl", "mark", 2.6), ("note", "sticky", 3.2), ("stamp", "stamp", 3.9)]),
    ("leap", 6.0, [("text", "write", 0.3), ("draw", "write", 0.3), ("burst", "burst", 1.6), ("hl", "mark", 2.6)]),
    ("dragon", 6.5, [("photo", "drop", 0.3), ("tape1", "tape", 0.75), ("text", "write", 1.2), ("glyph", "sticker", 2.6), ("doodle", "mark", 3.3)]),
    ("moral", 7.0, [("glyphs", "write", 0.3), ("quote", "write", 1.4), ("note", "sticky", 2.4), ("badge", "sticker", 4.0), ("stamp", "stamp", 4.6)]),
]
TRANS = 0.9
starts, t = [], 0.0
for _, dur, _e in PAGES: starts.append(t); t += dur
T = {
    "duration": round(t, 3), "fps": 24, "drawRate": 12, "trans": TRANS,
    "pages": [p[0] for p in PAGES],
    "start": starts,                                  # начало страницы (с этого момента начинается её перелистывание на неё)
    "B": starts[1:],                                  # моменты перелистывания
    "drawStart": [-0.5] + [s + 0.45 for s in starts[1:]],  # локальное время страницы отсчитывается отсюда
    "el": {},                                         # 'river.photo' -> локальное время
    "events": [],                                     # абсолютные события для звука
    "turn": starts[3] + 1.6,                          # поворот: вспышка наклеек на странице прыжка
}
for i, (pid, dur, els) in enumerate(PAGES):
    for name, kind, lt in els:
        T["el"][f"{pid}.{name}"] = lt
        T["events"].append({"t": round(T["drawStart"][i] + lt, 3), "kind": kind, "id": f"{pid}.{name}"})
T["events"].sort(key=lambda e: e["t"])
here = pathlib.Path(__file__).parent
(here / "timing.json").write_text(json.dumps(T, ensure_ascii=False, indent=1))
(here / "timing.js").write_text("window.T = " + json.dumps(T, ensure_ascii=False) + ";\n")
print("timing ok:", T["duration"], "s;", len(T["events"]), "events; turn at", T["turn"])
