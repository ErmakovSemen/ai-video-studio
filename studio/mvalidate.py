"""Валидатор нейромонтажа: сильная vision-модель проверяет B-roll вставки.

review_image  — по одной картинке: подходит ли по СМЫСЛУ к сказанному + выдержан ли СТИЛЬ
                + нет ли текста/артефактов. Возвращает вердикт и УЛУЧШЕННЫЙ промт.
review_cuts   — холистически по всем склейкам: получает картинки + таймлайны + текст,
                что проговаривается, и помечает слабые вставки с новым промтом.
"""
import os, json, base64, urllib.request

OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MONTAGE_VALIDATOR", "google/gemini-2.5-flash")
THRESHOLD = int(os.getenv("MONTAGE_VALIDATOR_THRESHOLD", "7"))
URL = "https://openrouter.ai/api/v1/chat/completions"


def _b64(p):
    return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()


def _chat(content):
    body = {"model": MODEL, "messages": [{"role": "user", "content": content}], "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    return r["choices"][0]["message"]["content"].strip()


def _json(txt):
    if "```" in txt:
        txt = txt.split("```")[1].lstrip("json").strip()
    a, b = txt.find("{"), txt.rfind("}")
    if a < 0:
        a, b = txt.find("["), txt.rfind("]")
    return json.loads(txt[a:b + 1])


def review_image(img_path, spoken, style):
    """Вердикт по одной B-roll картинке. -> {ok, score, reason, better_prompt}."""
    prompt = (
        "Ты — строгий арт-директор видеомонтажа. Проверь картинку-вставку (B-roll).\n"
        f"В этот момент в озвучке говорится: «{spoken}».\n"
        f"Требуемый визуальный стиль вставок: {style}.\n"
        "Оцени строго: (1) подходит ли картинка ПО СМЫСЛУ к сказанному; (2) выдержан ли "
        "СТИЛЬ; (3) нет ли на картинке текста/букв/водяных знаков/артефактов анатомии.\n"
        "Верни ТОЛЬКО JSON: {\"score\":0-10, \"meaning_ok\":bool, \"style_ok\":bool, "
        "\"has_text\":bool, \"reason\":\"<=15 слов почему\", \"better_prompt\":\"улучшенный "
        "английский промт картинки в том же стиле, чтобы исправить недостатки\"}")
    content = [{"type": "text", "text": prompt},
               {"type": "image_url", "image_url": {"url": _b64(img_path)}}]
    v, last = None, None
    for _ in range(2):                          # retry once if the model returns non-JSON
        try:
            v = _json(_chat(content)); break
        except Exception as e:
            last = e; v = None
    if v is None:                               # unparsed -> DON'T pass silently, force a retry
        return {"ok": False, "score": 0, "reason": f"validator unparsed: {last}", "better_prompt": None}
    v["ok"] = (bool(v.get("meaning_ok")) and bool(v.get("style_ok"))
               and not v.get("has_text") and int(v.get("score", 0)) >= THRESHOLD)
    return v


def review_cuts(items, style):
    """Холистическая проверка склеек. items=[{i,start,end,spoken,img}].
    -> {"issues":[{"index":i,"reason":..,"better_prompt":..}]}."""
    content = [{"type": "text", "text": (
        "Ты — арт-директор. Ниже — все B-roll вставки готового видео: для каждой её номер, "
        f"таймлайн, что проговаривается в этот момент, и сама картинка. Стиль: {style}.\n"
        "Оцени связность: каждая ли вставка уместна и в стиле, нет ли текста/артефактов, не "
        "выбивается ли какая-то. Верни ТОЛЬКО JSON {\"issues\":[{\"index\":номер, "
        "\"reason\":\"<=12 слов\", \"better_prompt\":\"новый английский промт в стиле\"}]} — "
        "только для проблемных; если всё ок, верни {\"issues\":[]}.")}]
    for it in items:
        content.append({"type": "text",
                        "text": f"#{it['i']} [{it['start']:.0f}-{it['end']:.0f}с] говорят: «{it['spoken']}»"})
        content.append({"type": "image_url", "image_url": {"url": _b64(it["img"])}})
    try:
        return _json(_chat(content))
    except Exception as e:
        return {"issues": [], "error": str(e)}
