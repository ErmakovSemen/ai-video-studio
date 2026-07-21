"""Оркестратор фабрики агентов. Один запуск = один шаг конвейера (приоритет ниже).
Вызывать по расписанию (cron/systemd timer). Совмещается с HEAVY_JOB_LOCK веб-приложения
через тот же контейнер — если из UI идёт рендер, следующий тик просто ничего не найдёт
готового и подождёт следующего раза (без гонок за память, всё в одном контейнере).
"""
import os, sys, traceback
from studio.factory import common as C, creator, producer, reviewer, director, analyst

PROJECT_SLUG = os.getenv("FACTORY_PROJECT", "chayniy")


def step_once(project_slug: str) -> str:
    project = C.load_project(project_slug)
    board = C.get_board(project)

    # 1) публикация — самый "дорогой по последствиям" шаг, но дешёвый по CPU
    if director.maybe_publish(project, board):
        return "director"
    # 2) ревью готовых рендеров
    if reviewer.maybe_review(project, board):
        return "reviewer"
    # 3) рендер следующей идеи (самый тяжёлый шаг по CPU/RAM)
    if producer.maybe_produce(project, board):
        return "producer"
    # 4) пополнить очередь идей
    if creator.maybe_create_idea(project, board):
        return "creator"
    # 5) раз в сутки — аналитика (обновляет инсайты для креатора)
    if analyst.maybe_analyze(project):
        return "analyst"
    return "idle"


def main():
    force = "--force" in sys.argv
    if not force and not C.autonomous_on():
        return                              # таймер вызвал, но автономный режим выключен
    # один шаг за раз — не запускать параллельные рендеры при частом тике таймера
    import fcntl
    lockf = open(C.STATE_DIR / "run.lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return                              # предыдущий шаг ещё идёт
    try:
        did = step_once(PROJECT_SLUG)
        C.log("run", f"шаг: {did}")
    except Exception as e:
        C.log("run", f"ОШИБКА: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
