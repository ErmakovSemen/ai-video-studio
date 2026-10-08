"""Единый источник: тексты глав и время появления каждого элемента.
Картинка (timing.js) берёт тексты и моменты, звук (audio.py) — события (буква, клавиша, скотч, печать…)."""
import json, pathlib

SCENES = [
    dict(id="legend", dur=9.5, label="1 · ЛЕГЕНДА", head="ШЭНЬ-НУН", obj="cauldron",
         note=["Император Шэнь-нун кипятил", "воду, и в котёл упал лист.", "Так, по легенде, появился чай"], seal="神农"),
    dict(id="tang", dur=9.0, label="2 · ДИНАСТИЯ ТАН", head="ЧА ЦЗИН", obj="book",
         note=["Около 760 года поэт Лу Юй", "пишет «Чайный канон» —", "первую в мире книгу о чае"], seal="唐"),
    dict(id="song", dur=9.5, label="3 · ДИНАСТИЯ СУН", head="ВЗБИТЫЙ ЧАЙ", obj="bowl",
         note=["Чай мелют в порошок и", "взбивают венчиком до пены.", "1191: монах Эйсай везёт", "этот обычай в Японию"], seal="宋"),
    dict(id="ming", dur=9.5, label="4 · ДИНАСТИЯ МИН", head="ЛИСТОВОЙ ЧАЙ", obj="teapot",
         note=["1391: указ императора —", "вместо прессованных плиток", "листовой чай, заваренный", "в чайнике"], seal="明"),
    dict(id="russia", dur=10.0, label="5 · ЧАЙ В РОССИИ", head="1638", obj="compass",
         note=["Посол Василий Старков", "привёз царю Михаилу", "4 пуда чая — подарок", "монгольского хана"], seal=None),
    dict(id="samovar", dur=8.5, label="6 · XIX ВЕК", head="САМОВАР", obj="samovar",
         note=["Тульские самовары", "делают чай народным", "напитком России"], seal=None),
    dict(id="today", dur=9.0, label="7 · СЕГОДНЯ", head="ЧАЙ", obj="cup",
         note=["Второй напиток в мире", "после воды"], seal="茶"),
]
TRANS, CPS = 0.6, 24          # смена листа (с); скорость машинки (знаков/с)
L = dict(label=0.0, head=0.25, letter=0.06, obj=1.1, ins1=1.9, ins2=2.4, note=2.9)
t = 0.0; T = {"fps": 24, "drawRate": 12, "trans": TRANS, "cps": CPS, "L": L, "scenes": [], "events": []}
for i, s in enumerate(SCENES):
    s = dict(s); s["start"] = round(t, 3); s["local0"] = round(t + (-0.8 if i == 0 else 0.45), 3)  # глава 1: заголовок уже на первом кадре  # время элементов отсчитывается отсюда
    nchar = sum(len(x) for x in s["note"])
    s["noteEnd"] = round(L["note"] + nchar / CPS + 0.1 * len(s["note"]), 3)
    s["sealAt"] = round(s["noteEnd"] + (1.1 if s["id"] == "today" else 0.3), 3)
    s["chipAt"] = round(s["noteEnd"] + 0.2, 3)
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
    if s["seal"] or i == 4: ev.append({"t": round(b + s["sealAt"], 3), "kind": "stamp"})
    if s["id"] == "today": ev += [{"t": round(b + s["chipAt"] + k * 0.15, 3), "kind": "slap"} for k in range(5)]
    if i > 0: ev.append({"t": s["start"], "kind": "sheet"})
    t += s["dur"]
T["duration"] = round(t, 3)
T["B"] = [s["start"] for s in T["scenes"][1:]]
T["events"] = sorted((e for e in T["events"] if e["t"] >= 0), key=lambda e: e["t"])
here = pathlib.Path(__file__).parent
(here / "timing.json").write_text(json.dumps(T, ensure_ascii=False, indent=1))
(here / "timing.js").write_text("window.T = " + json.dumps(T, ensure_ascii=False) + ";\n")
print("timing ok:", T["duration"], "s;", len(T["events"]), "events;", [s["noteEnd"] for s in T["scenes"]])
