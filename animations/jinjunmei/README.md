# Цзинь Цзюнь Мэй — карандашный мульт кодом

Метод: методичка «Мультики кодом» — HTML+canvas, рендер HyperFrames, звук синтезом. Без генераций.

- `STORYBOARD.md` — сценарий и раскадровка
- `timing.json` ← `build_timing.py` — единые константы времени (картинка и звук)
- `engine.js` — движок: карандаш, штриховка, рукопись, иероглиф, бумага, палитры по ролям
- `scenes.js` — сцены по раскадровке; `index.html` — композиция (`window.THEME` = `kraft` | `ink`)
- `audio.py` — синтез звука; `render.sh` — полная сборка; `sheet.sh` — лист кадров для самопроверки
- `GRABLI.md` — список граблей
- `out/` — готовые MP4 и листы кадров

Загрузка на YouTube: `python3 -m animations.jinjunmei.upload_youtube` (по умолчанию крафт) (нужны YT_* в env).

Сборка: `./render.sh all high`; с озвучкой: `VOICE=aleksandr-hq RATE=120 ./render.sh all high` (голоса офлайн: `apt install rhvoice rhvoice-russian`).
