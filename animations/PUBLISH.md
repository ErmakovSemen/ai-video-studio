# Публикация роликов на YouTube через Posty

Ролики заливаются на YouTube через **Posty** — коннектор (MCP), который держит токены YouTube сам. Свой OAuth-токен Google не нужен: в нём приложение стоит в режиме Testing, поэтому токен истекает через 7 дней, а ролики становятся приватными.

## Подключение (один раз, делает владелец)
1. **Канал в Posty.** На https://posty.hu войти и в разделе каналов подключить YouTube: вход через Google, выбрать канал.
2. **Posty как коннектор Claude.** На https://claude.ai/customize/connectors → Add custom connector → URL `https://api.posty.hu/mcp-oauth` → Connect (вход в Posty).
   Плагин Posty из облачной сессии напрямую не подключается: сеть среды не пускает к `api.posty.hu`. Кастомный коннектор ходит через сервер Anthropic, ему эта блокировка не мешает.
3. **Новая сессия.** Коннекторы подхватываются при старте сессии.

## Как публикует агент
1. `get_workspace_context`, затем `list_integrations` — найти YouTube-канал по id и `@handle`.
2. `upload_media_from_url` — загрузить ролик по публичной ссылке из GitHub (репозиторий публичный), например
   `https://raw.githubusercontent.com/ErmakovSemen/ai-video-studio/master/animations/teahistory/out/teahistory.mp4`.
3. `get_integration_schema` — лимиты YouTube. Заголовок, описание и теги взять из `<проект>/youtube.json`.
4. `preview_post` — показать владельцу превью. `create_post` вызывать только после его «да», с `idempotencyKey`.
5. Первую публикацию нового ролика делать **unlisted** (по ссылке), публичную — после просмотра владельцем.

Ролики 9:16 до 60 с YouTube сам относит к Shorts. «История чая» идёт 66,6 с, поэтому выйдет обычным вертикальным видео.
