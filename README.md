# AI Video Studio (переиспользуемый)

Свой пайплайн генерации коротких видео + простой UI.
Поток: описание (+опц. картинка) → [OpenRouter промпт] → [FAL Flux кадр / твоя картинка]
→ [FAL Kling image-to-video] → [edge-tts озвучка] → [ffmpeg склейка] → mp4 → скачать / автопост в TG.

## Провайдеры (приоритет)
- **OpenRouter video (по умолчанию, рекоменд.)** — Kling/Wan/Hailuo/Seedance через твои OR-кредиты,
  image-to-video, ~$0.63/клип (Kling std), регион-ок (не OpenAI/Google). Нужен OPENROUTER_API_KEY.
- **Hugging Face (бесплатно)** — публичные Spaces, без оплаты, но крошечная анон-квота (нужен free HF_TOKEN).
- **FAL** — опц. платный (FAL_KEY).
- **MOCK** — без сети (Ken-Burns + голос), для проверки потока.

## Pluggable
- FAL — адаптер (app/pipeline.py). Нет FAL_KEY → MOCK-режим (Ken-Burns по картинке/градиенту + голос),
  чтобы UI и поток работали без ключа. Меняется на другого провайдера без правки UI.

## Запуск
    python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
    FAL_KEY=... OPENROUTER_API_KEY=... AGT_TG_BOT_TOKEN=... \
      ./venv/bin/uvicorn app.main:app --port 8090
    открой http://127.0.0.1:8090

## ENV
- FAL_KEY            — ключ FAL.ai (без него MOCK)
- OPENROUTER_API_KEY — для рефайна промпта (опц.)
- AGT_TG_BOT_TOKEN   — бот для автопостинга в TG
- TG_CHANNEL         — канал (по умолч. @PrometeyApp)
- FAL_FLUX_MODEL / FAL_KLING_MODEL / TTS_VOICE — опц. оверрайды

## Статус
v1 скелет: UI + mock + озвучка + склейка + автопост в TG работают.
FAL-генерация подключается ключом (требует аккаунт+кредиты FAL, регион проверить).
