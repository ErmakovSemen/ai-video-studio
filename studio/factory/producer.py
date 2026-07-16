"""Агент-монтажёр/дизайнер: рендерит видео по сценарию идеи (TTS+картинки+монтаж+лауднорм)."""
import os, json, re, subprocess, time
from studio.factory import common as C


def _two_pass_loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    if not os.path.exists(src) or os.path.getsize(src) < 1000:
        raise RuntimeError(f"loudnorm: источник отсутствует/пуст: {src}")
    p1 = subprocess.run(["ffmpeg", "-i", src, "-af",
                         f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S)
    if not m:
        r = subprocess.run(["ffmpeg", "-y", "-i", src, "-c", "copy", dst], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(dst):
            raise RuntimeError(f"loudnorm: анализ громкости не сработал и fallback-копия не удалась: "
                               f"{r.stderr[-500:]}")
        return
    d = json.loads(m.group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    r = subprocess.run(["ffmpeg", "-y", "-i", src, "-af", af, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", dst],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError(f"loudnorm: финальный проход ffmpeg не сработал: {r.stderr[-500:]}")


def _load_scenario(card: dict) -> dict | None:
    """Карточка хранит сценарий либо inline-словарём (авто-креатор), либо путём к файлу
    (вручную засеянные идеи, формат _prod.py/_seed_ideas.py)."""
    sc = card.get("scenario")
    if isinstance(sc, dict):
        return sc
    if isinstance(sc, str):
        p = C.ROOT / sc
        if p.exists():
            from studio import story
            return story.load(str(p))
    return None


def maybe_produce(project: dict, board: dict) -> bool:
    ideas = C.col(board, "ideas")["cards"]
    card = None
    scenario = None
    for c in ideas:
        if c.get("rendering_failed"):
            continue
        scenario = _load_scenario(c)
        if scenario:
            card = c
            break
    if not card:
        return False

    from studio import imagegen, qc, story
    _orig = imagegen.generate_image
    imagegen.generate_image = lambda p, o, refs=None, model=None: qc.generate_checked(
        _orig, p, o, scene=p, refs=refs, tries=3)

    cid = card["id"]
    wd = str(C.ROOT / "work" / f"{cid}_{int(time.time())}")
    raw = str(C.OUT / f"{cid}_raw.mp4"); out = str(C.OUT / f"{cid}.mp4")
    music = str(C.ROOT / "assets" / "music" / "inspired.mp3")

    C.log("producer", f"рендерю '{card['title']}' ({cid})")
    try:
        story.build(scenario, raw, wd, base_dir=str(C.ROOT), draft=True,
                    gen_stills=True, polish=True, music=music if os.path.exists(music) else None,
                    captions=True)
        if not os.path.exists(raw) or os.path.getsize(raw) < 1000:
            raise RuntimeError(f"story.build не создал итоговый файл: {raw}")
        _two_pass_loudnorm(raw, out)
        if not os.path.exists(out) or os.path.getsize(out) < 1000:
            raise RuntimeError(f"после loudnorm итоговый файл отсутствует: {out}")
        if os.path.exists(raw):
            os.remove(raw)
    except Exception as e:
        C.log("producer", f"ОШИБКА рендера {cid}: {e}")
        card["rendering_failed"] = True
        card["retries"] = card.get("retries", 0) + 1
        C.save_board(project, board, message=f"factory: render failed {cid}")
        return True

    card["scenario"] = scenario          # нормализуем: дальше по конвейеру всегда inline-словарь
    card["video_path"] = f"outputs/{cid}.mp4"
    C.move_card(board, card, "ideas", "review")
    ok = C.save_board(project, board, message=f"factory: rendered {cid}")
    C.log("producer", f"рендер готов -> review {'ok' if ok else 'FAILED PUSH'}")
    return True
