"""Агент-директор: финальная упаковка (title/desc/tags) + публикация на YouTube + гейт по ритму."""
import json, os, time
from studio.factory import common as C

MIN_GAP_HOURS = float(os.getenv("FACTORY_MIN_GAP_HOURS", "4"))
MAX_RETRIES = int(os.getenv("FACTORY_MAX_RETRIES", "3"))
BACKOFF_MIN = int(os.getenv("FACTORY_BACKOFF_MIN", "30"))   # 30м -> 1ч -> 2ч


def _last_publish_ts(board: dict) -> float:
    ts = [c.get("published_at", 0) for c in C.col(board, "posted")["cards"]]
    return max(ts) if ts else 0


def maybe_publish(project: dict, board: dict) -> bool:
    # берём только живые карточки: сбойная не должна долбиться каждые 15 минут.
    # Именно так протухший YouTube-токен дал 1336 холостых коммитов за две недели.
    queue = [c for c in C.col(board, "await_post")["cards"]
             if not c.get("needs_human") and time.time() >= c.get("retry_after", 0)]
    if not queue:
        return False

    gap_h = (time.time() - _last_publish_ts(board)) / 3600
    if gap_h < MIN_GAP_HOURS:
        C.log("director", f"последний постинг {gap_h:.1f}ч назад (< {MIN_GAP_HOURS}ч) — жду")
        return False

    card = queue[0]
    cid = card["id"]
    path = C.ROOT / card.get("video_path", "")
    if not path.exists():
        C.log("director", f"{cid}: видео-файл потерян -> needs_human")
        card["needs_human"] = True
        C.save_board(project, board, message=f"factory: {cid} missing file at publish")
        return True

    title = card["title"][:100]
    desc = card.get("yt_desc") or card.get("desc") or ""
    tags = card.get("yt_tags") or []

    try:
        tok = json.load(open(C.ROOT / "yt_token.json"))
        os.environ.update(YT_CLIENT_ID=tok["client_id"], YT_CLIENT_SECRET=tok["client_secret"],
                          YT_REFRESH_TOKEN=tok["refresh_token"])
        from publish.youtube import YouTubePublisher
        from publish.base import VideoMeta
        res = YouTubePublisher().publish(str(path), VideoMeta(
            title=title, description=desc, tags=tags, category_id="27",
            privacy="public", made_for_kids=False))
    except Exception as e:
        n = card["retries"] = card.get("retries", 0) + 1
        card["publish_error"] = str(e)[:300]
        if n >= MAX_RETRIES:
            card.pop("retry_after", None)
            card["needs_human"] = True
            C.log("director", f"{cid}: ОШИБКА публикации ({n}/{MAX_RETRIES}) -> нужна помощь: {e}")
            C.notify(f"🔴 Прометей: не смог опубликовать «{card.get('title', cid)}» {n} раз подряд.\n"
                     f"Причина: {str(e)[:400]}\nКарточка ждёт человека, конвейер идёт дальше.")
        else:
            wait_min = BACKOFF_MIN * (2 ** (n - 1))
            card["retry_after"] = time.time() + wait_min * 60
            C.log("director", f"{cid}: ОШИБКА публикации ({n}/{MAX_RETRIES}), повтор через {wait_min}м: {e}")
        C.save_board(project, board, message=f"factory: {cid} publish failed ({n}/{MAX_RETRIES})")
        return True

    card.pop("retries", None); card.pop("retry_after", None); card.pop("publish_error", None)
    card["video"] = res["url"]
    card["published_at"] = time.time()
    C.move_card(board, card, "await_post", "posted")
    ok = C.save_board(project, board, message=f"factory: published {cid}")
    C.log("director", f"{cid}: опубликовано {res['url']} {'ok' if ok else 'FAILED PUSH'}")
    return True
