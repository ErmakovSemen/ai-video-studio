"""Кошелёк воркспейса: баланс в ₽, журнал транзакций, промокоды, пополнения.

ВАЖНО про деньги: настоящего приёма платежей здесь НЕТ и быть не может без
мерчант-аккаунта владельца. Модуль реализует всё, что вокруг платежа:
  - баланс и журнал (кто, когда, за что),
  - промокоды (в т.ч. снимающие комиссию),
  - заявку на пополнение и её подтверждение.
Само зачисление вызывается методом `confirm_topup()`. Его дёргает:
  - вебхук платёжного провайдера (когда владелец подключит ключи), либо
  - владелец вручную из админки, если оплата пришла переводом.
Так деньги ходят на кошелёк владельца у провайдера, а продукт лишь отражает факт.
"""
import json
import secrets
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)
WALLET_FILE = CONFIG_DIR / "wallet.json"
PROMO_FILE = CONFIG_DIR / "promo.json"

# Комиссия сервиса на пополнение (наценка). Промокод может её обнулить.
FEE_PCT = 5

# Прайс разовых операций, ₽ (себестоимость ~8-10₽, см. billing.py)
PRICE = {"video": 39, "montage": 59, "clip": 59}


def _read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _wallet() -> dict:
    w = _read(WALLET_FILE, {})
    w.setdefault("balance", 0)
    w.setdefault("tx", [])
    w.setdefault("pending", {})
    return w


def balance() -> int:
    return int(_wallet().get("balance", 0))


def transactions(limit: int = 50) -> list:
    return _wallet().get("tx", [])[:limit]


def _add_tx(w: dict, kind: str, amount: int, note: str = "", extra: dict = None):
    w["tx"].insert(0, {"id": secrets.token_hex(6), "kind": kind, "amount": int(amount),
                       "note": note, "ts": int(time.time()), "balance_after": int(w["balance"]),
                       **(extra or {})})
    w["tx"] = w["tx"][:400]


# ---------- промокоды ----------
def _promos() -> dict:
    return _read(PROMO_FILE, {})


def promo_list() -> list:
    out = []
    for code, p in _promos().items():
        out.append({"code": code, **p})
    return out


def promo_create(code: str, kind: str = "no_fee", value: int = 0,
                 uses: int = 0, days: int = 0) -> dict:
    """kind: no_fee (без комиссии) | bonus_pct (+% к сумме) | bonus_fixed (+₽).
    uses=0 -> без ограничения; days=0 -> бессрочно."""
    code = code.strip().upper()
    if not code:
        raise ValueError("Пустой код")
    p = _promos()
    p[code] = {"kind": kind, "value": int(value), "uses_left": int(uses) or None,
               "expires": (int(time.time()) + days * 86400) if days else None,
               "used": 0, "created": int(time.time())}
    _write(PROMO_FILE, p)
    return {"code": code, **p[code]}


def promo_delete(code: str) -> bool:
    p = _promos()
    if code.strip().upper() in p:
        p.pop(code.strip().upper())
        _write(PROMO_FILE, p)
        return True
    return False


def promo_check(code: str) -> dict:
    """-> {valid, kind, value, reason}"""
    code = (code or "").strip().upper()
    if not code:
        return {"valid": False, "reason": ""}
    p = _promos().get(code)
    if not p:
        return {"valid": False, "reason": "Промокод не найден"}
    if p.get("expires") and p["expires"] < time.time():
        return {"valid": False, "reason": "Срок действия промокода истёк"}
    if p.get("uses_left") is not None and p["uses_left"] <= 0:
        return {"valid": False, "reason": "Промокод больше не действует"}
    return {"valid": True, "code": code, "kind": p["kind"], "value": p["value"]}


def _promo_consume(code: str):
    p = _promos()
    if code in p:
        p[code]["used"] = p[code].get("used", 0) + 1
        if p[code].get("uses_left") is not None:
            p[code]["uses_left"] = max(0, p[code]["uses_left"] - 1)
        _write(PROMO_FILE, p)


def quote(amount: int, promo: str = "") -> dict:
    """Расчёт пополнения до оплаты: сколько списать и сколько зачислить."""
    amount = max(0, int(amount))
    pr = promo_check(promo)
    fee_pct = FEE_PCT
    bonus = 0
    if pr.get("valid"):
        if pr["kind"] == "no_fee":
            fee_pct = 0
        elif pr["kind"] == "bonus_pct":
            bonus = round(amount * pr["value"] / 100)
        elif pr["kind"] == "bonus_fixed":
            bonus = int(pr["value"])
    fee = round(amount * fee_pct / 100)
    return {"amount": amount, "fee_pct": fee_pct, "fee": fee, "bonus": bonus,
            "to_pay": amount + fee, "to_credit": amount + bonus,
            "promo": pr if promo else None}


# ---------- пополнение ----------
def create_topup(amount: int, promo: str = "", method: str = "manual") -> dict:
    """Заявка на пополнение. Реального списания здесь нет — его делает провайдер."""
    q = quote(amount, promo)
    if q["amount"] <= 0:
        raise ValueError("Укажите сумму пополнения")
    w = _wallet()
    tid = secrets.token_hex(8)
    # промокод кладём ПОСЛЕ распаковки quote: там ключ promo — это словарь проверки,
    # и он затирал сам код (ловил на тесте)
    w["pending"][tid] = {"id": tid, "created": int(time.time()), "method": method,
                         **q, "promo": (promo or "").strip().upper()}
    _write(WALLET_FILE, w)
    return {"id": tid, **q}


def pending_list() -> list:
    return sorted(_wallet().get("pending", {}).values(), key=lambda x: -x["created"])


def confirm_topup(tid: str) -> dict:
    """Зачислить пополнение. Вызывается вебхуком провайдера или владельцем вручную."""
    w = _wallet()
    p = w.get("pending", {}).pop(tid, None)
    if not p:
        raise ValueError("Заявка не найдена или уже проведена")
    w["balance"] = int(w.get("balance", 0)) + int(p["to_credit"])
    note = f"Пополнение на {p['amount']}₽"
    if p.get("bonus"):
        note += f" + бонус {p['bonus']}₽"
    if p.get("promo"):
        note += f" (промокод {p['promo']})"
    _add_tx(w, "topup", p["to_credit"], note, {"promo": p.get("promo", "")})
    _write(WALLET_FILE, w)
    if p.get("promo"):
        _promo_consume(p["promo"])
    return {"ok": True, "balance": w["balance"], "credited": p["to_credit"]}


def cancel_topup(tid: str) -> bool:
    w = _wallet()
    if w.get("pending", {}).pop(tid, None):
        _write(WALLET_FILE, w)
        return True
    return False


# ---------- списания ----------
def can_charge(op: str) -> dict:
    price = PRICE.get(op, 0)
    bal = balance()
    return {"ok": bal >= price, "price": price, "balance": bal}


def charge(op: str, note: str = "") -> dict:
    """Списать за операцию. Возвращает {ok, balance} — при нехватке не списывает."""
    price = PRICE.get(op, 0)
    w = _wallet()
    if int(w.get("balance", 0)) < price:
        return {"ok": False, "balance": int(w.get("balance", 0)), "price": price}
    w["balance"] = int(w["balance"]) - price
    _add_tx(w, "charge", -price, note or {"video": "Ролик", "montage": "Нейромонтаж",
                                          "clip": "Нарезка на Shorts"}.get(op, op))
    _write(WALLET_FILE, w)
    return {"ok": True, "balance": w["balance"], "price": price}


def status() -> dict:
    return {"balance": balance(), "fee_pct": FEE_PCT, "price": PRICE,
            "tx": transactions(20), "pending": pending_list()}
