"""Единый источник: тексты глав и время появления каждого элемента.
Картинка (timing.js) берёт тексты и моменты, звук (audio.py) — события (буква, клавиша, скотч, печать…).
Каждая глава — «шаг доказательства» с логической ловушкой (trap — для себя, в кадре не показывается): в конце штамп «ДОКАЗАНО»."""
import json, pathlib

SCENES = [
    dict(id="paws", dur=9.5, label="ШАГ 1 · СИЛЛОГИЗМ", head="4 ЛАПЫ", obj="cat",
         note=["У мопса четыре лапы.", "У кошки четыре лапы.", "Следовательно,", "кошка — мопс."], trap="общий признак"),
    dict(id="poll", dur=9.0, label="ШАГ 2 · ОПРОС", head="100%", obj="pug",
         note=["Мы опросили трёх мопсов.", "Все трое уверены:", "кошки — это мопсы"], trap="кривая выборка"),
    dict(id="prof", dur=9.0, label="ШАГ 3 · НАУКА", head="ПРОФЕССОР", obj="prof",
         note=["Профессор Мопсон,", "доктор мопсологии,", "лично подтвердил"], trap="ложный авторитет"),
    dict(id="dict", dur=10.0, label="ШАГ 4 · ТЕРМИНЫ", head="СЛОВАРЬ", obj="cat",
         note=["Мопс — любое существо,", "что спит 16 часов в день.", "Кошка спит 16 часов.", "Вопросы?"], trap="подмена понятий"),
    dict(id="face", dur=10.0, label="ШАГ 5 · ФАКТЫ", head="ПЕРС", obj="cat",
         note=["У персидской кошки", "плоская морда, как", "у мопса. Значит, все", "кошки — мопсы"], trap="поспешный вывод"),
    dict(id="none", dur=9.0, label="ШАГ 6 · ПРОВЕРКА", head="ОБРАТНОЕ?", obj="loupe",
         note=["Никто не доказал,", "что кошка — НЕ мопс.", "Значит, мопс"], trap="довод к незнанию"),
    dict(id="qed", dur=9.5, label="ШАГ 7 · ИТОГ", head="Ч.Т.Д.", obj="pug",
         note=["Кошка возражает?", "Так возражают", "только мопсы"], trap="порочный круг"),
]
TRANS, CPS = 0.6, 24          # смена листа (с); скорость машинки (знаков/с)
COVER = 1.6                   # обложка «Все кошки — мопсы» стоит с первого кадра
L = dict(label=0.0, head=0.25, letter=0.06, obj=1.1, ins1=1.9, ins2=2.4, note=2.9)
t = COVER; T = {"fps": 24, "drawRate": 12, "trans": TRANS, "cps": CPS, "L": L, "cover": COVER, "scenes": [], "events": []}
for i, s in enumerate(SCENES):
    s = dict(s); s["start"] = round(t, 3); s["local0"] = round(t + 0.45, 3)  # время элементов отсчитывается отсюда
    nchar = sum(len(x) for x in s["note"])
    s["noteEnd"] = round(L["note"] + nchar / CPS + 0.1 * len(s["note"]), 3)
    s["sealAt"] = round(s["noteEnd"] + 0.35, 3)          # штамп «ДОКАЗАНО»
    T["scenes"].append(s)
    b = s["local0"]
    ev = T["events"]
    ev.append({"t": b + L["label"], "kind": "slide"})
    for k, ch in enumerate(s["head"]):
        if ch != " ": ev.append({"t": round(b + L["head"] + k * L["letter"], 3), "kind": "letter"})
    ev += [{"t": b + L["obj"], "kind": "drop"}, {"t": b + L["ins1"], "kind": "tape"}, {"t": b + L["ins2"], "kind": "slap"}]
    tt = b + L["note"]
    for line in s["note"]:
        for ch in line:
            if ch != " ": ev.append({"t": round(tt, 3), "kind": "key"})
            tt += 1 / CPS
        ev.append({"t": round(tt, 3), "kind": "return"}); tt += 0.1
    ev.append({"t": round(b + s["sealAt"], 3), "kind": "stamp"})
    ev.append({"t": s["start"], "kind": "sheet"})
    t += s["dur"]
T["duration"] = round(t, 3)
T["B"] = [s["start"] for s in T["scenes"]]
T["events"] = sorted((e for e in T["events"] if e["t"] >= 0), key=lambda e: e["t"])
here = pathlib.Path(__file__).parent
(here / "timing.json").write_text(json.dumps(T, ensure_ascii=False, indent=1))
(here / "timing.js").write_text("window.T = " + json.dumps(T, ensure_ascii=False) + ";\n")
print("timing ok:", T["duration"], "s;", len(T["events"]), "events")
