"""Единый источник времени: картинка (timing.js) и звук (audio.py) берут одни константы.
Все моменты — во «времени сюжета»; паузы на чтение (holds) раздвигают его до реального."""
import json, pathlib

T = {
    "storyDuration": 40.0,
    "fps": 24,
    "drawRate": 12,
    "walkCycle": 1.2,               # полный цикл ходьбы, с (два шага)
    # окна ходьбы: [кто, начало, конец, x0, x1]
    "walks": [["student", 0.0, 4.2, -140, 470], ["monk", 6.0, 8.6, 1130, 760], ["red", 18.2, 22.4, -120, 600]],
    "fall": 4.7,                    # студент падает
    "pour": [9.2, 10.6],            # монах наливает чай
    "drink": 12.2,
    "turn": 16.0,                   # поворот: свиток 状元 (40% длины)
    "stamp": 16.5,
    "throw": 25.8,                  # мантия брошена
    "drape": 27.0,                  # мантия легла на кусты
    "posterFrom": 33.0,
    "draw": [[0.0, 2.6], [17.6, 18.6], [33.0, 34.3]],
    "plucks": [1.2, 2.6, 6.4, 7.6, 9.0, 11.6],
    "motif": [18.4, 19.0, 19.6, 20.2, 22.9, 23.4],
    "finalChord": 33.0,
}
T["holds"] = [[17.0, 0.8]]
T["duration"] = round(T["storyDuration"] + sum(h[1] for h in T["holds"]), 3)
steps = []
for who, a, b, *_ in T["walks"]:
    t = a + T["walkCycle"] / 4
    while t < b: steps.append(round(t, 3)); t += T["walkCycle"] / 2
T["steps"] = steps

here = pathlib.Path(__file__).parent
(here / "timing.json").write_text(json.dumps(T, ensure_ascii=False, indent=1))
(here / "timing.js").write_text("window.T = " + json.dumps(T) + ";\n")
print("timing ok:", T["duration"], "s,", len(steps), "steps")
