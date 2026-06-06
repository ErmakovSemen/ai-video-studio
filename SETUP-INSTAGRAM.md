# Подключение Instagram Reels

Постинг Reels идёт через **Instagram Graph API**. Нужен бизнес-аккаунт и
Facebook-приложение (это делаешь ты).

## Предусловия
- Аккаунт Instagram переключён в **Business** или **Creator**.
- Он привязан к **Facebook-странице**.

## Шаги
1. https://developers.facebook.com/ → создай приложение (тип Business).
2. Добавь продукт **Instagram Graph API**. Права: `instagram_content_publish`,
   `instagram_basic`, `pages_show_list`.
3. Получи **долгоживущий access token** (long-lived, ~60 дней) для страницы/аккаунта.
4. Узнай **IG user id** (числовой id Instagram-аккаунта; через Graph API Explorer:
   `me/accounts` → `instagram_business_account`).
5. В приложении (раздел «5 · Подключение соцсетей») вставь **access token** и **ig_user_id**.

## Как это работает
Graph API забирает видео по публичной ссылке, поэтому ролик сначала автоматически
заливается на временный публичный хост (catbox.moe), затем создаётся Reels-контейнер
и публикуется. Токен живёт ~60 дней — потом обнови его в настройках.
