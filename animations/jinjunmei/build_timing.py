"""Единый источник времени: картинка (timing.js) и звук (audio.py) берут одни константы."""
import json, pathlib

N_BUDS = 24
T = {
    "duration": 20.0,
    "fps": 24,
    "drawRate": 12,            # рисунков в секунду (на двойках)
    "turn": 8.0,               # поворот: вспышка почки (40% длины)
    "rainStart": 10.1,
    "budStep": 0.065,
    "glyphs": [13.0, 14.1, 15.2],
    "seal": 16.9,
    "posterFrom": 17.0,
    # окна, когда карандаш активно рисует -> шорох
    "draw": [[0.0, 3.8], [4.0, 6.4], [7.0, 7.95], [8.05, 9.6], [13.0, 16.0], [16.1, 17.0]],
    # щипки пентатоники до поворота (холодно)
    "plucks": [1.0, 2.2, 4.3, 5.0, 5.8, 6.6],
    # мотив после поворота (тепло)
    "motif": [8.6, 9.0, 9.4, 9.8],
    "finalChord": 16.1,
}
T["budLand"] = [round(T["rainStart"] + i * T["budStep"], 4) for i in range(N_BUDS)]
# паузы на чтение: [момент сюжета, длительность]. Сюжет замирает, линии продолжают кипеть.
T["holds"] = [[6.0, 1.2], [9.6, 0.8], [12.05, 1.4]]
T["storyDuration"] = T["duration"]
T["duration"] = round(T["storyDuration"] + sum(h[1] for h in T["holds"]), 3)

here = pathlib.Path(__file__).parent
(here / "timing.json").write_text(json.dumps(T, ensure_ascii=False, indent=1))
(here / "timing.js").write_text("window.T = " + json.dumps(T) + ";\n")
print("timing ok:", T["duration"], "s,", len(T["budLand"]), "buds")
