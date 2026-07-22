"""Генерация сценария ролика из свободного текста (идеи пользователя).
Общий код для ручного создания (/api/create) и автономного агента-креатора
(studio/factory/creator.py) — чтобы не дублировать промт и парсинг."""
import re
from studio.factory import common as C

MAX_SCENES = 7

SYS_TMPL = """{brand_prompt}

Ты создаёшь сценарий короткого вертикального видео (YouTube Shorts, 25-40 сек)
по идее пользователя.

Методика хука: сильнее всего удерживают внимание любопытство/интрига и лёгкая
эмоциональная зацепка — держат досмотр лучше чисто инструктивных роликов.
Первая фраза должна создавать открытый вопрос или сильный контраст, который
зритель хочет закрыть, досмотрев до конца.
{extra}
Верни ТОЛЬКО JSON:
{{
  "slug": "короткий_id_латиницей_snake_case",
  "title": "заголовок видео с эмодзи, до 90 символов",
  "hook": "первая фраза сценария — самая сильная, интригующая",
  "desc": "описание под YouTube, 2-4 предложения, заканчивай призывом в духе бренда",
  "tags": ["тег1","тег2","тег3","тег4","тег5"],
  "scenes": [
    {{"image": "английское описание кадра для художника, БЕЗ текста на картинке, в заданном стиле",
      "motion": "английское краткое описание движения камеры/элементов",
      "vo": "русский текст озвучки для этой сцены, 1-2 короткие фразы",
      "caption": "короткая подпись на экране, 2-4 слова"}}
  ]
}}
Сцен: 5-{max_scenes}, каждая — новый визуальный бит, vo вместе складывается в связный текст ролика."""


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return (s or "video")[:40]


def generate(idea: str, project: dict, avoid_topics: str = "", extra_instruction: str = "") -> dict:
    """idea: свободный текст пользователя. project: dict из projects/<slug>/project.json.
    Возвращает {"slug","title","hook","desc","tags","scenario": {...render-ready...}}."""
    extra = ""
    if avoid_topics:
        extra += f"\nНЕ повторяй уже раскрытые темы:\n{avoid_topics}\n"
    if extra_instruction:
        extra += f"\nВАЖНОЕ УТОЧНЕНИЕ от пользователя: {extra_instruction}\n"
    sys = SYS_TMPL.format(brand_prompt=project.get("system_prompt", ""), extra=extra,
                          max_scenes=MAX_SCENES)
    usr = f"Идея пользователя: {idea}"
    txt = C.call_llm(sys, usr, temperature=0.85)
    data = C.parse_json(txt)

    slug = _slugify(data.get("slug") or data["title"])
    scenario = {
        "title": data["title"], "hook": data["hook"],
        "voice": project.get("voice", "ru-RU-DmitryNeural"),
        "hero": next(iter(project.get("characters", {})), None),
        "brand_image": project.get("brand_image"), "characters": project.get("characters", {}),
        "style": project.get("style", ""), "scenes": data["scenes"][:MAX_SCENES],
    }
    return {"slug": slug, "title": data["title"], "hook": data["hook"],
            "desc": data.get("desc", ""), "tags": data.get("tags", []), "scenario": scenario}
