"""Story cartoon factory — scenario (JSON/dict) -> finished cartoon mp4.

A scenario is pure data, so this is reusable across projects/brands. Stages:
1. per scene: generate scene image (consistent via character refs) -> animate -> narrate
2. trim each clip to its narration (sync), burn caption
3. end-card + stitch (narration muxed over video)

Scenario schema:
{
  "title": str,
  "brand_image": path,                      # used for end-card
  "characters": {name: path, ...},          # reusable reference art
  "style": str,                             # style preamble for every scene image
  "scenes": [
     {"image": str, "refs": [name,...], "motion": str, "vo": str, "caption": str}, ...
  ],
  "endcard": {"title": str, "sub": str, "vo": str}
}
"""
import os, json
from studio import imagegen, video, compose

PAD = 0.35  # seconds of trailing silence per scene so cuts breathe


def build(scenario: dict, out_path: str, workdir: str, base_dir: str = ".",
          draft: bool = False, polish: bool = False, music: str = None,
          gen_stills: bool = False, stills_dir: str | None = None) -> dict:
    """Render a scenario into a cartoon.

    draft=True       → FREE: Ken-Burns on the reference art, for flow/timing.
    draft+stills_dir → FREE rich render: Ken-Burns on PRE-BAKED per-scene stills
                       (stills_dir/scene{i}.png, committed once) — full-bleed scenes,
                       greece-level quality, zero per-run cost. Falls back to ref art
                       for any scene whose still is missing.
    draft+gen_stills → cheap rich render: generate the scene image via Gemini (per-scene
                       composition) then Ken-Burns on it — no Kling, ~cents/scene.
    polish=True      → montage layer: word-level KARAOKE captions (real edge-tts timing)
                       + optional ducked music bed. Works with both draft and final clips.
    """
    from studio import edit
    os.makedirs(workdir, exist_ok=True)
    chars = {k: os.path.join(base_dir, v) for k, v in scenario.get("characters", {}).items()}
    style = scenario.get("style", "")
    scene_videos, voice_segs = [], []
    words_global = []           # [(word, start_s, end_s)] over the final timeline (polish)
    t = 0.0                     # running timeline offset (polish)
    log = {"title": scenario.get("title"), "draft": draft, "polish": polish, "scenes": []}

    for i, sc in enumerate(scenario["scenes"]):
        refs = [chars[name] for name in sc.get("refs", []) if name in chars]
        raw = os.path.join(workdir, f"raw{i}.mp4")
        vo = os.path.join(workdir, f"vo{i}.mp3")
        if polish:
            dur, words = edit.tts_timed(sc["vo"], vo)
        else:
            compose.tts(sc["vo"], vo); dur = compose.dur(vo)
        seconds = dur + PAD
        img = None
        baked = os.path.join(stills_dir, f"scene{i}.png") if stills_dir else None
        if draft and baked and os.path.exists(baked):
            img = baked
            compose.mock_clip(baked, sc.get("caption", sc["vo"]), seconds, raw)
        elif draft and gen_stills:
            img = os.path.join(workdir, f"img{i}.png")
            no_text = (" IMPORTANT: absolutely NO text, NO letters, NO words, NO captions, "
                       "NO writing, NO watermark, NO signs anywhere in the image — clean illustration only.")
            imagegen.generate_image(f"{style} SCENE: {sc['image']}{no_text}", img, refs)
            compose.mock_clip(img, sc.get("caption", sc["vo"]), seconds, raw)
        elif draft:
            compose.mock_clip(refs[0] if refs else None, sc.get("caption", sc["vo"]), seconds, raw)
        else:
            img = os.path.join(workdir, f"img{i}.png")
            imagegen.generate_image(f"{style} SCENE: {sc['image']}", img, refs)
            video.animate(img, sc["motion"], raw)
        sv = os.path.join(workdir, f"sc{i}.mp4")
        if polish:
            edit.trim(raw, seconds, sv)                    # no burned caption
            for w, a, b in words:
                words_global.append([w, t + a, t + b])
        else:
            compose.scene_clip(raw, sc.get("caption", ""), seconds, sv)
        # First-second grab: bold hook line over scene 0 (retention lever for Shorts)
        hook = scenario.get("hook") if i == 0 else None
        if hook:
            hv = os.path.join(workdir, f"sc{i}_hook.mp4")
            compose.burn_hook(sv, hook, hv); sv = hv
        sil = os.path.join(workdir, f"sil{i}.mp3"); compose.silence(sil, PAD)
        scene_videos.append(sv)
        voice_segs.append(vo); voice_segs.append(sil)
        t += seconds
        log["scenes"].append({"img": img, "clip": sv, "dur": round(seconds, 2)})

    ec = scenario.get("endcard", {})
    if ec:
        ecvo = os.path.join(workdir, "voEC.mp3")
        if polish:
            ecdur, ecwords = edit.tts_timed(ec.get("vo", ""), ecvo)
        else:
            compose.tts(ec.get("vo", ""), ecvo); ecdur = compose.dur(ecvo)
        ecsec = ecdur + 0.7
        ecv = os.path.join(workdir, "scEC.mp4")
        compose.endcard(os.path.join(base_dir, scenario["brand_image"]),
                        ec.get("title", ""), ec.get("sub", ""), ecsec, ecv)
        scene_videos.append(ecv)
        ecsil = os.path.join(workdir, "voECsil.mp3"); compose.silence(ecsil, 0.7)
        voice_segs.append(ecvo); voice_segs.append(ecsil)
        # endcard shows its own branded title/CTA — skip karaoke captions there for a clean outro
        if polish:
            t += ecsec

    if polish:
        _assemble_polished(scene_videos, voice_segs, words_global, out_path, workdir, music)
    else:
        compose.stitch(scene_videos, voice_segs, out_path, workdir)
    log["out"] = out_path
    return log


def _assemble_polished(clips, voice_segs, words, out_path, workdir, music):
    """Hard-cut concat (keeps A/V in sync) + karaoke captions + optional music."""
    import subprocess
    from studio import edit
    FF = compose.FF
    # concat video (no audio)
    vlst = os.path.join(workdir, "pv.txt")
    open(vlst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in clips))
    vcat = os.path.join(workdir, "pvcat.mp4")
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", vlst,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", vcat],
                   capture_output=True)
    # concat narration (vo + silence segments)
    ins = []
    for v in voice_segs:
        ins += ["-i", v]
    fc = "".join(f"[{i}:a]" for i in range(len(voice_segs))) + \
         f"concat=n={len(voice_segs)}:v=0:a=1[a]"
    acat = os.path.join(workdir, "pacat.m4a")
    subprocess.run([FF, "-y", *ins, "-filter_complex", fc, "-map", "[a]", acat],
                   capture_output=True)
    # karaoke captions over the whole timeline
    ass = os.path.join(workdir, "caps.ass")
    edit.karaoke_ass(words, ass, group=3)
    edit.finalize(vcat, acat, out_path, ass=ass, music=music)
    return out_path


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
