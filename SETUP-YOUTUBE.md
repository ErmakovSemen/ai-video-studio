# Подключение автопостинга в YouTube

Это нужно сделать **один раз**. Я (агент) не могу создавать аккаунты и вводить
пароли/токены — поэтому шаги в Google Cloud делаешь ты, а весь код и финальная
склейка токена — на мне. Займёт ~10 минут.

## Что получится
Сервер сам заливает готовые ролики на твой YouTube-канал (как Shorts), без браузера,
по «refresh-токену». В UI завода появится кнопка **▲ В YouTube Shorts**.

---

## Шаг 1. Google Cloud проект + API
1. Зайди на https://console.cloud.google.com/ под нужным Google-аккаунтом (на котором канал).
2. Сверху создай проект (напр. `prometey-studio`).
3. APIs & Services → **Library** → найди **YouTube Data API v3** → **Enable**.

## Шаг 2. OAuth consent screen
1. APIs & Services → **OAuth consent screen** → User type **External** → Create.
2. Заполни обязательное (название приложения `Prometey Studio`, твой email). Сохраняй до конца.
3. На шаге **Test users** добавь свой Google-аккаунт (тот, где канал). 
   *(Пока приложение в режиме Testing, постить можно только под test-аккаунтами — этого достаточно.)*
4. Scopes можно не добавлять руками — код просит `youtube.upload` сам.

## Шаг 3. OAuth client (Desktop)
1. APIs & Services → **Credentials** → **Create Credentials** → **OAuth client ID**.
2. Application type: **Desktop app** → Create.
3. Скопируй **Client ID** и **Client secret** (или нажми Download JSON → `client_secret.json`).

## Шаг 4. Получить refresh-токен (локально, 1 команда)
В папке репозитория:
```bash
pip install -r requirements.txt          # если ещё не ставил
export YT_CLIENT_ID=<твой client id>
export YT_CLIENT_SECRET=<твой client secret>
python -m publish.youtube_auth
```
Откроется браузер → выбери аккаунт с каналом → **Allow**.
В консоль напечатает три строки:
```
YT_CLIENT_ID=...
YT_CLIENT_SECRET=...
YT_REFRESH_TOKEN=...
```

## Шаг 5. Прописать на сервере (Render)
Render → сервис `ai-video-studio` → **Environment** → добавь три переменные:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (значения из шага 4) → **Save** (сервис передеплоится).

Готово. В UI раздел «4 · Публикация» покажет `YouTube Shorts: ✅ готово`,
и кнопка зальёт последнее отрендеренное видео.

---

## Важный нюанс про видимость
Пока OAuth-приложение **не прошло аудит Google**, ролики, залитые через API,
**принудительно становятся `private`**. Варианты:
- заливать автоматически как `private`/`unlisted` и руками публиковать (1 клик в YouTube Studio), **или**
- пройти аудит Google (форма в OAuth consent screen) — тогда станет можно сразу `public`.

Для старта годится первый вариант: автопостинг работает, публичность — один ручной клик.
Я держу это в коде (выбор приватности в UI).

## Квоты
Дефолтная квота — 10 000 единиц/день, заливка = 1600 ед → ~6 роликов/день. С запасом.
