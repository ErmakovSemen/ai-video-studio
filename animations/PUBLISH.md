# Публикация роликов

Ролики публикует GitHub Actions — workflow **Publish video** (`.github/workflows/publish-video.yml`), скрипт `scripts/publish_video.py` поверх `publish/` (YouTube, Telegram, TikTok, Instagram). Это бесплатно и не требует сервера. Агент запускает workflow сам через GitHub из любой сессии; настраивать сеть среды не нужно.

## Запуск
- Параметры: `project` — папка ролика с `out/*.mp4` и `youtube.json`; `platforms` — `youtube,telegram,…`; `privacy` — `unlisted` для первой заливки; `tg_channel` — канал Telegram.
- Заголовок, описание и теги берутся из `<project>/youtube.json`.
- Результат (id и ссылки) — в логе запуска.

## Ключи (секреты репозитория)
- **YouTube:** `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`. Чтобы токен не сгорал через 7 дней, приложение в Google Cloud нужно перевести в «In production». Пока Google не проверит приложение (аудит YouTube API), залитые ролики остаются приватными.
- **Telegram:** `AGT_TG_BOT_TOKEN`; канал — `TG_CHANNEL` или параметр `tg_channel`. Бот должен быть администратором канала.
- **TikTok, Instagram:** в `publish/` код уже есть, в workflow ещё не подключены; см. `SETUP-TIKTOK.md`, `SETUP-INSTAGRAM.md`.
