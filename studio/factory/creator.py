"""Агент-креатор: придумывает новую идею ролика и кладёт карточку в колонку "Идеи"."""
import re, time, uuid
from studio.factory import common as C

MIN_IDEAS = 2          # если в очереди идей >= этого числа — не генерим новую
MAX_SCENES = 7

SYS_TMPL = """{brand_prompt}

Ты придумываешь ОДНУ новую идею короткого вертикального видео (YouTube Shorts, 25-40 сек).

Методика хука (по данным аналитики канала): сильнее всего удерживают внимание
любопытство/интрига и лёгкая эмоциональная зацепка (чувство вины/самоуважения,
сторителлинг) — держат досмотр лучше чисто инструктивных роликов ("как заварить...").
Инструктивные хуки дают больше кликов, но хуже досматриваются — используй их редко.
Первая фраза должна создавать открытый вопрос или сильный контраст, который зритель
хочет закрыть, досмотрев до конца.

ВАЖНО: не повторяй уже раскрытые темы (список ниже) — нужен новый угол/факт/история.

Уже раскрыто:
{used_topics}

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


def _used_topics(project: dict, board: dict) -> str:
    titles = []
    for c in board.get("columns", []):
        for card in c.get("cards", []):
            t = card.get("title")
            if t:
                titles.append(t)
    sdir = C.ROOT / "scenarios" / project.get("scenarios_dir", project["id"])
    if sdir.is_dir():
        for f in sdir.glob("*.json"):
            titles.append(f.stem)
    return "\n".join(f"- {t}" for t in titles[-60:]) or "(пока нет)"


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return (s or "idea")[:40]


def maybe_create_idea(project: dict, board: dict) -> bool:
    ideas = C.col(board, "ideas")["cards"]
    if len(ideas) >= MIN_IDEAS:
        C.log("creator", f"в очереди уже {len(ideas)} идей, пропускаю")
        return False

    ipath = C.STATE_DIR / f"insights_{project['id']}.md"
    insights = ipath.read_text(encoding="utf-8") if ipath.exists() else ""
    brand_prompt = project.get("system_prompt", "")
    sys = SYS_TMPL.format(brand_prompt=brand_prompt, used_topics=_used_topics(project, board),
                          max_scenes=MAX_SCENES)
    usr = "Придумай новую идею." + (f"\n\nЧто узнали из аналитики прошлых видео:\n{insights}" if insights else "")

    txt = C.call_llm(sys, usr, temperature=0.9)
    data = C.parse_json(txt)

    slug = _slugify(data.get("slug") or data["title"])
    scenario = {
        "title": data["title"], "hook": data["hook"],
        "voice": project["voice"], "hero": next(iter(project.get("characters", {})), None),
        "brand_image": project.get("brand_image"), "characters": project.get("characters", {}),
        "style": project["style"], "scenes": data["scenes"][:MAX_SCENES],
    }
    card = {
        "id": f"idea_{slug}_{int(time.time())}", "title": data["title"], "desc": data.get("hook", ""),
        "scenario": scenario, "yt_desc": data.get("desc", ""), "yt_tags": data.get("tags", []),
        "tags": ["auto", "creator"], "created": int(time.time()), "retries": 0,
    }
    ideas.append(card)
    ok = C.save_board(project, board, message=f"factory: new idea {slug}")
    C.log("creator", f"новая идея '{data['title']}' -> board {'ok' if ok else 'FAILED PUSH'}")
    return True
