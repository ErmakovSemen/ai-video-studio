"""ИИ-монтажёр (v1): LLM-проход по сценарию, улучшающий субтитры/текст.

Движок монтажа — FFmpeg (studio/edit.py, compose.py). «Мозги» — LLM через OpenRouter
(работает в регионе РФ). Монтажёр анализирует закадровый текст сцен и выдаёт:
  - чистую панч-подпись (caption) под каждый кадр (без опечаток, короче, цепляет),
  - ключевое слово для эмфазы (выделяем крупнее/цветом),
  - (опц.) подсказку оверлея.
Результат — улучшенный сценарий (scenarios/<name>_ai.json) + план правок
(<name>_ai.plan.json), готовые к рендеру существующим пайплайном.
"""
import os
import json
import urllib.request

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
EDIT_MODEL = os.getenv("OR_EDIT_MODEL", "meta-llama/llama-3.3-70b-instruct")


def _chat(messages, temperature=0.4, max_tokens=1500) -> str:
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_API_KEY required")
    body = {"model": EDIT_MODEL, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                                          "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    return r["choices"][0]["message"]["content"]


SYS = (
    "Ты — ИИ-монтажёр коротких вертикальных видео (Shorts/Reels/TikTok) про дисциплину. "
    "На входе — закадровые реплики сцен. Для КАЖДОЙ сцены верни улучшение субтитра:\n"
    "- caption: короткая цепляющая подпись на экран (2–5 слов, БЕЗ опечаток, разговорно, "
    "усиливает смысл реплики; можно слегка перефразировать, но смысл сохрани),\n"
    "- emphasis: ОДНО ключевое слово из caption, которое выделить (точно как в caption),\n"
    "- overlay: короткая подсказка оверлея или \"\" (напр. \"стрелка вниз\", \"🔥\", \"\").\n"
    "Верни СТРОГО JSON-массив объектов [{\"caption\":\"\",\"emphasis\":\"\",\"overlay\":\"\"}], "
    "по одному на сцену, в том же порядке. Без пояснений, только JSON."
)


def improve_captions(scenario: dict) -> list[dict]:
    """LLM -> список правок субтитров по сценам (по порядку scenes)."""
    lines = [f"{i+1}. {sc.get('vo','')}" for i, sc in enumerate(scenario.get("scenes", []))]
    user = "Реплики сцен:\n" + "\n".join(lines) + \
           f"\n\nВерни ровно {len(lines)} объектов JSON-массивом."
    raw = _chat([{"role": "system", "content": SYS}, {"role": "user", "content": user}])
    # вытащить JSON-массив из ответа
    s = raw.find("["); e = raw.rfind("]")
    if s < 0 or e < 0:
        raise RuntimeError(f"LLM did not return JSON: {raw[:200]}")
    plan = json.loads(raw[s:e+1])
    return plan


def ai_edit(scenario_path: str, out_scenario: str | None = None) -> dict:
    """Полный проход: грузим сценарий -> LLM улучшает субтитры -> пишем улучшенный
    сценарий + план. Возвращает {scenario, plan, paths}."""
    sc = json.load(open(scenario_path, encoding="utf-8"))
    plan = improve_captions(sc)
    scenes = sc.get("scenes", [])
    for i, p in enumerate(plan[:len(scenes)]):
        cap = (p.get("caption") or "").strip()
        if cap:
            scenes[i]["caption"] = cap
            scenes[i]["emphasis"] = (p.get("emphasis") or "").strip()
            if p.get("overlay"):
                scenes[i]["overlay"] = p["overlay"].strip()
    base = os.path.splitext(scenario_path)[0]
    out_scenario = out_scenario or f"{base}_ai.json"
    plan_path = f"{base}_ai.plan.json"
    sc["title"] = sc.get("title", "") + " · ИИ-монтаж"
    json.dump(sc, open(out_scenario, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(plan, open(plan_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"scenario": out_scenario, "plan": plan_path, "edits": plan}


if __name__ == "__main__":
    import sys
    res = ai_edit(sys.argv[1])
    print(json.dumps(res, ensure_ascii=False, indent=2))
