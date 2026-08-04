"""Язык камеры: единый словарь съёмочных приёмов для всего пайплайна.

Зачем это существует. Раньше сцена несла поле motion — свободную строку от LLM
(«slow pan», «camera moves»). Дальше строка шла в две совершенно разные точки:
в image-to-video модель (Kling/Higgsfield) и в ffmpeg-черновик. Модель трактовала
её как придётся, а черновик игнорировал вовсе и крутил один и тот же медленный
зум на каждой сцене — ролик выглядел вялым и одинаковым.

Здесь приём — это набор из четырёх согласованных вещей:
  prompt     — формулировка на языке, который модели реально понимают,
  ff         — ffmpeg-фильтр, дающий тот же приём бесплатно, без генерации;
               {p} в нём — прогресс сцены 0..1, поэтому приём укладывается
               ровно в её длительность, а не «сгорает» за первые две секунды,
  genre/ramp — параметры Higgsfield cinematic_studio (жанр и тайм-эффект),
  beat       — драматургическая роль: где в ролике приём уместен.

Итог: платный и бесплатный тракт дают ОДНУ И ТУ ЖЕ раскадровку, отличаясь
только фотореализмом. Черновик перестаёт быть заглушкой и становится
предсказуемым превью того, что получится за деньги.
"""
from __future__ import annotations

# beat: hook — первые секунды, надо остановить пролистывание;
#       build — тело, ровное внимание; payoff — вывод, вес и точка.
SHOTS: dict[str, dict] = {
    "push_in": {
        "label": "Наезд",
        "prompt": "slow steady dolly push-in toward the subject, shallow depth of field",
        "ff": "zoompan=z='1+0.22*{p}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "genre": "intimate", "ramp": "linear", "beat": "build",
    },
    "pull_back": {
        "label": "Отъезд-раскрытие",
        "prompt": "slow dolly pull-back revealing the wider scene around the subject",
        "ff": "zoompan=z='1.24-0.22*{p}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "genre": "spectacle", "ramp": "linear", "beat": "payoff",
    },
    "crash_zoom": {
        "label": "Резкий наезд",
        "prompt": "fast aggressive crash zoom into the subject, punchy and abrupt",
        "ff": "zoompan=z='1+0.5*pow({p},2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "genre": "action", "ramp": "impact", "beat": "hook",
    },
    "orbit": {
        "label": "Облёт",
        "prompt": "smooth arc orbit around the subject, parallax between foreground and background",
        "ff": "zoompan=z='1.16':x='iw/2-(iw/zoom/2)+sin({p}*3.14159)*(iw/13)':y='ih/2-(ih/zoom/2)'",
        "genre": "spectacle", "ramp": "linear", "beat": "build",
    },
    "tilt_up": {
        "label": "Панорама вверх",
        "prompt": "slow vertical tilt up the subject, ending on a heroic low angle",
        "ff": "zoompan=z='1.18':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1-{p})'",
        "genre": "spectacle", "ramp": "slowmo", "beat": "payoff",
    },
    "handheld": {
        "label": "С рук",
        "prompt": "handheld documentary camera, subtle organic shake, natural imperfection",
        "ff": "zoompan=z='1.1':x='iw/2-(iw/zoom/2)+sin(on/7)*7':y='ih/2-(ih/zoom/2)+cos(on/9)*6'",
        "genre": "auto", "ramp": "auto", "beat": "build",
    },
    "whip_pan": {
        "label": "Хлыст",
        "prompt": "fast whip pan across the scene with motion blur, energetic transition",
        "ff": "zoompan=z='1.22':x='(iw-iw/zoom)*{p}':y='ih/2-(ih/zoom/2)'",
        "genre": "action", "ramp": "speedup", "beat": "hook",
    },
    "static_hold": {
        "label": "Статика",
        "prompt": "locked-off static shot, absolutely no camera movement, only the subject breathes",
        "ff": "zoompan=z='1.02':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "genre": "suspense", "ramp": "auto", "beat": "payoff",
    },
    "fpv_dive": {
        "label": "FPV-пролёт",
        "prompt": "fpv drone dive flying through the scene toward the subject, high energy",
        "ff": "zoompan=z='1+0.35*{p}':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1-0.75*{p})'",
        "genre": "action", "ramp": "speedup", "beat": "hook",
    },
}

DEFAULT = "push_in"
# Что ставим, если LLM промолчала: по такту, а не одно и то же на весь ролик.
BY_BEAT = {"hook": "crash_zoom", "build": "push_in", "payoff": "pull_back"}


def ids() -> list[str]:
    return list(SHOTS)


def vocabulary() -> str:
    """Список приёмов для промпта сценариста — читаемый и коротким."""
    return "\n".join(f'  "{k}" — {v["label"]}: {v["prompt"]}' for k, v in SHOTS.items())


def beat_of(i: int, total: int) -> str:
    """Такт сцены по её месту в ролике."""
    if total <= 1 or i == 0:
        return "hook"
    return "payoff" if i >= total - 1 else "build"


def resolve(shot: str | None, i: int = 0, total: int = 1) -> dict:
    """Приём по id. Неизвестный/пустой id -> приём, уместный для такта сцены.

    Так ролик не разваливается, если модель вернула отсебятину: подставляем
    осмысленный приём, а не молча роняем всё в один и тот же зум.
    """
    key = (shot or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key not in SHOTS:
        key = BY_BEAT.get(beat_of(i, total), DEFAULT)
    return {"id": key, **SHOTS[key]}


def prompt_for(scene: dict, i: int = 0, total: int = 1) -> str:
    """Промпт движения для image-to-video. Уважает старое поле motion.

    Сцены, сгенерированные до появления словаря, несут только motion —
    его текст остаётся ведущим, а приём добавляет недостающую конкретику.
    """
    sh = resolve(scene.get("shot"), i, total)
    legacy = (scene.get("motion") or "").strip().rstrip(".,")
    parts = [legacy] if legacy else []
    parts.append(sh["prompt"])
    return ", ".join(parts) + ", subtle minimal cinematic motion, keep the subject stable"


def ff_filter(scene: dict, i: int, total: int, w: int, h: int, frames: int, fps: int = 30) -> str:
    """Тот же приём для бесплатного черновика: строка -vf для ffmpeg.

    Плейсхолдер {p} разворачивается в прогресс сцены 0..1, поэтому приём
    отрабатывает ровно за её длительность — и на двухсекундной, и на
    десятисекундной. Дрожание handheld намеренно считает по `on`: тряска
    должна идти с постоянной частотой, а не растягиваться вместе со сценой.
    """
    sh = resolve(scene.get("shot"), i, total)
    zp = sh["ff"].replace("{p}", f"(on/{max(1, frames - 1)})")
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"{zp}:d={frames}:s={w}x{h}:fps={fps},format=yuv420p")


def hf_params(scene: dict, i: int = 0, total: int = 1) -> dict:
    """Параметры Higgsfield cinematic_studio под приём: жанр и тайм-эффект."""
    sh = resolve(scene.get("shot"), i, total)
    return {"genre": sh["genre"], "speedramp": sh["ramp"]}
