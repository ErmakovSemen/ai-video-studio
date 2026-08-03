"""Тарифы, учёт использования и квоты.

Модель монетизации: ПАКЕТ (подписка с включённым объёмом) + оверадж сверх квоты.
Почему не «процент с использования»: процент требует, чтобы у клиента были свои
ключи к ИИ-провайдерам (иначе не с чего считать процент), а это ровно то, чего мы
избегаем — клиент не должен возиться с ключами. Пакет даёт клиенту предсказуемый
счёт (малый бизнес не любит плавающие суммы), а нам — маржу опт/розница.

Себестоимость (расчёт по актуальным ценам моделей OpenRouter на 2026-07):
  сценарий (Sonnet 4.5)  ~1.5k in + 1.5k out          ≈ $0.027
  кадры (Gemini Flash Image) ~6 сцен × ~2.5 попытки QC ≈ $0.048
  QC-проверки кадров                                   ≈ $0.010
  ---------------------------------------------------------------
  ИТОГО ролик «с нуля»                                 ≈ $0.085 (~8₽)
  нейромонтаж/нарезка: воркер ~5.3₽/ч × ~0.25ч + вставки ≈ ~10₽
Инфраструктура: веб-узел ~1371₽/мес.
Цифры — расчётные (померить эмпирически не удалось: баланс исчерпан).
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)
USAGE_FILE = CONFIG_DIR / "usage.json"
PLAN_FILE = CONFIG_DIR / "plan.json"

# Тарифы. quota=None -> безлимит. model_tier влияет на качество генерации.
PLANS = {
    "trial": {
        "id": "trial", "name": "Пробный", "price": 0, "period": "",
        "tagline": "Попробовать, как это работает",
        "quota": {"video": 3, "montage": 1, "clip": 1},
        "model_tier": "basic", "autopilot": False,
        "features": ["3 ролика", "Базовое качество", "Без автопилота"],
    },
    "start": {
        "id": "start", "name": "Старт", "price": 990, "period": "мес",
        "tagline": "Для тех, кто ведёт один канал",
        "quota": {"video": 15, "montage": 3, "clip": 3},
        "model_tier": "basic", "autopilot": False,
        "features": ["15 роликов в месяц", "Нейромонтаж и нарезка", "Публикация в соцсети",
                     "Ручной режим"],
    },
    "flow": {
        "id": "flow", "name": "Поток", "price": 3900, "period": "мес",
        "tagline": "Контент выходит сам, каждый день",
        "quota": {"video": 60, "montage": 20, "clip": 20},
        "model_tier": "quality", "autopilot": True, "popular": True,
        "features": ["60 роликов в месяц", "Повышенное качество генерации",
                     "Автопилот 24/7", "Нейромонтаж и нарезка", "Аналитика и обучение на ней"],
    },
    "studio": {
        "id": "studio", "name": "Студия", "price": 11900, "period": "мес",
        "tagline": "Для агентств и нескольких каналов",
        "quota": {"video": 250, "montage": None, "clip": None},
        "model_tier": "max", "autopilot": True,
        "features": ["250 роликов в месяц", "Максимальное качество",
                     "Безлимитный монтаж и нарезка", "Автопилот 24/7", "Приоритетная очередь"],
    },
}

# Что тарифицируем и сколько это стоит нам (₽, для оверажда и прозрачности)
OP_COST = {"video": 8, "montage": 10, "clip": 10}
OVERAGE = {"video": 39, "montage": 59, "clip": 59}   # цена сверх квоты, ₽

MODEL_TIERS = {
    "basic":   {"text": "google/gemini-2.5-flash", "label": "базовое"},
    "quality": {"text": "anthropic/claude-sonnet-4.5", "label": "повышенное"},
    "max":     {"text": "anthropic/claude-sonnet-4.5", "label": "максимальное"},
}


def current_plan() -> dict:
    """Активный тариф воркспейса. По умолчанию — пробный."""
    try:
        pid = json.loads(PLAN_FILE.read_text(encoding="utf-8")).get("plan")
        if pid in PLANS:
            return PLANS[pid]
    except Exception:
        pass
    return PLANS[os.getenv("DEFAULT_PLAN", "trial")]


def set_plan(plan_id: str) -> bool:
    if plan_id not in PLANS:
        return False
    PLAN_FILE.write_text(json.dumps({"plan": plan_id, "since": int(time.time())},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def _period() -> str:
    return time.strftime("%Y-%m")


def _usage() -> dict:
    try:
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def usage_now() -> dict:
    """Использование за текущий месяц: {"video": n, ...}."""
    return _usage().get(_period(), {})


def record(op: str, n: int = 1):
    """Зафиксировать операцию. Основа и для пакетов, и для оверажда."""
    data = _usage()
    p = _period()
    data.setdefault(p, {})
    data[p][op] = data[p].get(op, 0) + n
    # держим историю компактной — последние 13 месяцев
    for k in sorted(data.keys())[:-13]:
        data.pop(k, None)
    try:
        USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def check(op: str) -> dict:
    """Можно ли выполнить операцию. -> {allowed, used, limit, left, reason}."""
    plan = current_plan()
    limit = plan["quota"].get(op)
    used = usage_now().get(op, 0)
    if limit is None:
        return {"allowed": True, "used": used, "limit": None, "left": None}
    left = max(0, limit - used)
    if left <= 0:
        return {"allowed": False, "used": used, "limit": limit, "left": 0,
                "reason": f"На тарифе «{plan['name']}» закончился лимит на этот месяц "
                          f"({limit}). Смените тариф, чтобы продолжить."}
    return {"allowed": True, "used": used, "limit": limit, "left": left}


def status() -> dict:
    plan = current_plan()
    used = usage_now()
    quota = {}
    for op, limit in plan["quota"].items():
        u = used.get(op, 0)
        quota[op] = {"used": u, "limit": limit,
                     "left": (None if limit is None else max(0, limit - u))}
    return {"plan": {k: plan[k] for k in ("id", "name", "price", "period", "tagline",
                                          "model_tier", "autopilot", "features")},
            "quota": quota, "period": _period(),
            "model_label": MODEL_TIERS.get(plan["model_tier"], {}).get("label", "")}


def text_model() -> str:
    """Модель под тариф — так «повышенное качество» становится реальным отличием."""
    tier = current_plan()["model_tier"]
    return MODEL_TIERS.get(tier, MODEL_TIERS["basic"])["text"]


def plans_public() -> list:
    return [PLANS[k] for k in ("start", "flow", "studio")]
