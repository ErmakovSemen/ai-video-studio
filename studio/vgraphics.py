"""Vision-детекция наложенной графики в кадре (плашки/таблицы/титры/логотипы).

Сэмплит кадры видео и спрашивает сильную vision-модель, в каких вертикальных третях
есть графика, добавленная монтажом (а не естественная часть сцены). По результату
компоновщик ставит вставку в СВОБОДНУЮ зону и не перекрывает чужой монтаж.
"""
import os, json, base64, subprocess, urllib.request
from studio import edit

FF = edit.FF
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MONTAGE_VISION", "google/gemini-2.5-flash")


def _b64(path):
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def _ask(img_data):
    prompt = ("На изображении — стоп-кадр видео. Есть ли ПОВЕРХ видео наложенная монтажом "
              "графика: таблица, нижняя плашка (lower-third), титры/субтитры, логотип, рамка — "
              "то, что добавлено при монтаже, а НЕ естественная часть снятой сцены (не мебель, "
              "не предметы в кадре)? Ответь ТОЛЬКО JSON: {\"top\":bool,\"middle\":bool,"
              "\"bottom\":bool} — в каких третях кадра ПО ВЕРТИКАЛИ присутствует такая графика.")
    body = {"model": MODEL, "temperature": 0, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": img_data}}]}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"})
    txt = json.load(urllib.request.urlopen(req, timeout=60))["choices"][0]["message"]["content"].strip()
    if "```" in txt:
        txt = txt.split("```")[1].lstrip("json").strip()
    a, b = txt.find("{"), txt.rfind("}")
    return json.loads(txt[a:b + 1])


def detect_at(video, t, wd):
    """Занятые графикой зоны В КОНКРЕТНЫЙ момент t (сек). -> ['bottom', ...]."""
    f = os.path.join(wd, f"gat{int(t * 10)}.png")
    subprocess.run([FF, "-y", "-ss", f"{max(0, t):.1f}", "-i", video, "-frames:v", "1", f], capture_output=True)
    if not os.path.exists(f):
        return []
    try:
        r = _ask(_b64(f))
        return sorted(k for k in ("top", "middle", "bottom") if r.get(k))
    except Exception:
        return []


def detect_bands(video, wd, n=6):
    """-> {counts, n, occupied:[зоны, где графика ПОЯВЛЯЕТСЯ хотя бы временами]}.
    Порог низкий: для карточки лучше избегать зоны, даже если графика непостоянна."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nk=1:nw=1", video], capture_output=True, text=True).stdout or 1)
    counts, got = {"top": 0, "middle": 0, "bottom": 0}, 0
    for i in range(n):
        t = dur * (i + 1) / (n + 1)
        f = os.path.join(wd, f"gprobe{i}.png")
        subprocess.run([FF, "-y", "-ss", f"{t:.1f}", "-i", video, "-frames:v", "1", f], capture_output=True)
        if not os.path.exists(f):
            continue
        try:
            r = _ask(_b64(f)); got += 1
            for k in counts:
                if r.get(k):
                    counts[k] += 1
        except Exception:
            pass
    occ = sorted(k for k, v in counts.items() if got and v >= max(2, round(got * 0.3)))
    return {"counts": counts, "n": got, "occupied": occ}
