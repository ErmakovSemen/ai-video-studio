# Подключение Higgsfield (генерация видео)

Higgsfield — платный AI-видеогенератор (image→video, кинематографичное движение).
Код-провайдер уже встроен (`studio/higgsfield.py`), осталось задать ключ и переключить
провайдера. **Платно** — генерация тратит кредиты Higgsfield, поэтому по мандату запуск
финального видео выносится на апрув.

## 1. Получить ключ
1. Зайти на https://platform.higgsfield.ai (или cloud.higgsfield.ai), войти.
2. Dashboard → API keys → создать ключ. Формат: `KEY_ID:KEY_SECRET`.

## 2. Задать env (на Render и/или локально в .secrets.env)
```
HIGGSFIELD_API_KEY=KEY_ID:KEY_SECRET   # обязательно
VIDEO_PROVIDER=higgsfield               # переключить с openrouter на higgsfield
# опционально (значения по умолчанию):
HIGGSFIELD_BASE=https://platform.higgsfield.ai
HIGGSFIELD_PATH=/v1/image2video/dop
HIGGSFIELD_MODEL=turbo
HIGGSFIELD_AUTH=key                      # "key" -> "Authorization: Key …"; "bearer" если нужен Bearer
```
На Render — через дашборд Environment или Render API. В GitHub Secrets (для Action) —
`gh secret set HIGGSFIELD_API_KEY`.

## 3. Проверить
`GET /api/health` → должно показать `"higgsfield_ready": true` и `"video_provider": "higgsfield"`.

## Как это работает
- `studio/video.py` `animate(image, motion, out)` диспетчеризует по `VIDEO_PROVIDER`:
  `openrouter` (Kling, по умолчанию) или `higgsfield`.
- Higgsfield: картинка заливается на публичный хост (catbox) → `POST /v1/image2video/dop`
  `{model, prompt, input_images, aspect_ratio:9:16}` → поллинг `GET /requests/{id}/status`
  → скачивание `video.url`.
- Финальный (не-draft) рендер `story.build(draft=False)` вызывает `video.animate` на каждую
  сцену. Бесплатные пути (board «Сгенерировать видео» = draft, autopost) Higgsfield НЕ трогают.

## Важно
- Точная форма REST-тела может отличаться от версии аккаунта/SDK — всё вынесено в env
  (`HIGGSFIELD_PATH`, `HIGGSFIELD_MODEL`, `HIGGSFIELD_AUTH`); при ошибке формата поправить
  без правки кода. Если структура ответа иная — `_find_video_url` ищет `video.url`
  рекурсивно, но при экзотике может потребоваться доводка.
- Это деньги: первый прогон делать на 1 сцене и под апрувом.
