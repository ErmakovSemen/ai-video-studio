# Да Хун Пао — легенда о красной мантии (карандашный мульт кодом)

Метод: методичка «Мультики кодом» — HTML+canvas, рендер HyperFrames, звук синтезом. Без генераций.

- `STORYBOARD.md` — сценарий и раскадровка
- `timing.json` ← `build_timing.py` — константы времени: моменты смены карточек и вид перехода (по ним же звуки бумаги), свиток, поворот
- `engine.js` — карандашный движок (общий с jinjunmei)
- `scenes.js` — карточки-иллюстрации и бумажные переходы (`crumple`, `fold`, `unroll`); `index.html` — композиция (`window.THEME` = `kraft` | `ink`)
- `audio.py` — звук; `render.sh` — сборка; `sheet.sh` — лист кадров
- `out/dahongpao_kraft.mp4` — готовый ролик (31.5 с), `out/sheet.png` — лист кадров

Сборка: `./render.sh kraft high` (~2 мин).
