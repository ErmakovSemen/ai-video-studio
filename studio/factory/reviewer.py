"""Агент-ревьюер: факт-чек и оценка качества хука по сценарию + техническая проверка файла."""
import os
from studio.factory import common as C

MAX_RETRIES = 2

SYS = """Ты — строгий редактор контента чайного/просветительского канала Shorts.
Тебе даны заголовок, хук и озвучка (по сценам) готового видео.
Проверь:
1) ФАКТЫ — нет ли фактических ошибок или сомнительных утверждений (если не уверен — пометь).
2) ХУК — реально ли первая фраза цепляет и создаёт интригу, а не просто описание.
3) СВЯЗНОСТЬ — держится ли повествование, нет ли обрыва мысли между сценами.
Верни ТОЛЬКО JSON: {"ok": bool, "reason": "кратко почему", "fix_vo": ["новая озвучка сцены 1", ...] или null}
fix_vo — только если ok=false и проблему можно решить переписав озвучку (тот же порядок сцен,
то же количество строк, что и сцен). Если проблема не в тексте (например файл битый) — fix_vo: null."""


def maybe_review(project: dict, board: dict) -> bool:
    review = C.col(board, "review")["cards"]
    card = next((c for c in review if not c.get("needs_human")), None)
    if not card:
        return False

    cid = card["id"]
    path = C.ROOT / card.get("video_path", "")
    if not path.exists() or path.stat().st_size < 10_000:
        C.log("reviewer", f"{cid}: файл видео отсутствует/пустой -> needs_human")
        card["needs_human"] = True
        C.save_board(project, board, message=f"factory: {cid} bad file")
        return True

    scenario = card.get("scenario", {})
    scenes = scenario.get("scenes", [])
    usr = (f"Заголовок: {card['title']}\nХук: {scenario.get('hook','')}\n\nОзвучка по сценам:\n" +
           "\n".join(f"{i+1}. {s.get('vo','')}" for i, s in enumerate(scenes)))

    try:
        txt = C.call_llm(SYS, usr, temperature=0.2)
        res = C.parse_json(txt)
    except Exception as e:
        C.log("reviewer", f"{cid}: ошибка ревью-модели ({e}) -> needs_human")
        card["needs_human"] = True
        C.save_board(project, board, message=f"factory: {cid} review error")
        return True

    if res.get("ok"):
        C.move_card(board, card, "review", "await_post")
        C.save_board(project, board, message=f"factory: approved {cid}")
        C.log("reviewer", f"{cid}: одобрено -> await_post")
        return True

    retries = card.get("retries", 0)
    reason = res.get("reason", "")
    fix_vo = res.get("fix_vo")
    if retries >= MAX_RETRIES or not fix_vo or len(fix_vo) != len(scenes):
        C.log("reviewer", f"{cid}: отклонено ({reason}), лимит попыток исчерпан -> needs_human")
        card["needs_human"] = True
        card["reject_reason"] = reason
        C.save_board(project, board, message=f"factory: {cid} rejected, needs human")
        return True

    for s, vo in zip(scenes, fix_vo):
        s["vo"] = vo
    card["retries"] = retries + 1
    card["rendering_failed"] = False
    for k in ("video_path",):
        card.pop(k, None)
    C.move_card(board, card, "review", "ideas")
    C.save_board(project, board, message=f"factory: {cid} sent back for re-render ({reason})")
    C.log("reviewer", f"{cid}: отклонено ({reason}) -> ideas на перерендер (попытка {card['retries']})")
    return True
