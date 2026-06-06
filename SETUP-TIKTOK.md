# Подключение TikTok

Постинг в TikTok идёт через **Content Posting API**. Нужен разработческий аккаунт
и приложение (это делаешь ты — я не создаю аккаунты).

## Шаги
1. https://developers.tiktok.com/ → войди, **Manage apps** → создай приложение.
2. Добавь продукт **Content Posting API** (и **Login Kit**). Scope: `video.publish`
   (и `video.upload`).
3. Возьми **Client key** и **Client secret**.
4. Пройди OAuth, чтобы получить **refresh token** со scope `video.publish`
   (через redirect-флоу твоего приложения; можно временным скриптом, как с YouTube —
   скажи, помогу собрать).
5. В приложении (раздел «5 · Подключение соцсетей») вставь Client key / secret /
   refresh token и поле privacy (`SELF_ONLY` для черновиков, `PUBLIC_TO_EVERYONE`
   после аудита).

## Важно
Пока приложение **не прошло аудит TikTok**, посты уходят в черновики/inbox аккаунта
(публично не публикуются). Это нормально для старта: ролик заливается автоматически,
публикуешь в один тап в приложении TikTok. После аудита — сразу public.
