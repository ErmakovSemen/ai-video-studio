"""Единый источник времени: картинка (timing.js) и звук (audio.py) берут одни константы."""
import json, pathlib

# Ролик-книжка: статичные карточки, переходы — бумага (смять/перевернуть/развернуть свиток)
B = [5.2, 9.8, 13.9, 19.0, 25.5]                     # моменты смены карточек
KIND = ["crumple", "fold", "fold", "crumple", "fold"]
TRANS = 0.9                                          # длительность перехода
UNROLL = [14.6, 15.1]                                # свиток (карточка 4) разворачивается
DRAW = [-0.5, B[0] + 0.5, B[1] + 0.5, 15.0, B[3] + 0.5, B[4] + 0.5]  # начало прорисовки каждой карточки
T = {
    "duration": 31.5, "storyDuration": 31.5, "fps": 24, "drawRate": 12,
    "B": B, "kind": KIND, "trans": TRANS, "unroll": UNROLL, "drawStart": DRAW,
    "turn": UNROLL[0],                                # поворот: 状元 (≈46% длины — свиток раскрывается к 15.1)
    "pour": [DRAW[2] + 1.8, DRAW[2] + 3.4],
    "stamp": DRAW[3] + 1.4,
    "holds": [],
    "draw": [[max(0, s), s + 2.6] for s in DRAW],      # окна прорисовки -> шорох карандаша
    "plucks": [0.6, 2.0, 6.2, 7.4, 10.8, 12.0],
    "motif": [16.0, 16.6, 17.2, 20.2, 21.0, 22.4],
    "finalChord": DRAW[5] + 0.3,
}
here = pathlib.Path(__file__).parent
(here / "timing.json").write_text(json.dumps(T, ensure_ascii=False, indent=1))
(here / "timing.js").write_text("window.T = " + json.dumps(T) + ";\n")
print("timing ok:", T["duration"], "s; cards at", B)
