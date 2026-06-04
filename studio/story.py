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
          draft: bool = False) -> dict:
    """Render a scenario into a cartoon. draft=True is FREE (no Gemini/Kling):
    Ken-Burns on the reference art + narration + captions — for previewing flow/timing."""
    os.makedirs(workdir, exist_ok=True)
    chars = {k: os.path.join(base_dir, v) for k, v in scenario.get("characters", {}).items()}
    style = scenario.get("style", "")
    scene_videos, voice_segs = [], []
    log = {"title": scenario.get("title"), "draft": draft, "scenes": []}

    for i, sc in enumerate(scenario["scenes"]):
        refs = [chars[name] for name in sc.get("refs", []) if name in chars]
        raw = os.path.join(workdir, f"raw{i}.mp4")
        vo = os.path.join(workdir, f"vo{i}.mp3")
        compose.tts(sc["vo"], vo)
        seconds = compose.dur(vo) + PAD
        img = None
        if draft:
            compose.mock_clip(refs[0] if refs else None, sc.get("caption", sc["vo"]), seconds, raw)
        else:
            img = os.path.join(workdir, f"img{i}.png")
            imagegen.generate_image(f"{style} SCENE: {sc['image']}", img, refs)
            video.animate(img, sc["motion"], raw)
        sv = os.path.join(workdir, f"sc{i}.mp4")
        compose.scene_clip(raw, sc.get("caption", ""), seconds, sv)
        # narration + trailing silence so the audio length == the clip length (stays in sync)
        sil = os.path.join(workdir, f"sil{i}.mp3"); compose.silence(sil, PAD)
        scene_videos.append(sv)
        voice_segs.append(vo); voice_segs.append(sil)
        log["scenes"].append({"img": img, "clip": sv, "dur": round(seconds, 2)})

    ec = scenario.get("endcard", {})
    if ec:
        ecvo = os.path.join(workdir, "voEC.mp3"); compose.tts(ec.get("vo", ""), ecvo)
        ecsec = compose.dur(ecvo) + 0.7
        ecv = os.path.join(workdir, "scEC.mp4")
        compose.endcard(os.path.join(base_dir, scenario["brand_image"]),
                        ec.get("title", ""), ec.get("sub", ""), ecsec, ecv)
        scene_videos.append(ecv)
        ecsil = os.path.join(workdir, "voECsil.mp3"); compose.silence(ecsil, 0.7)
        voice_segs.append(ecvo); voice_segs.append(ecsil)

    compose.stitch(scene_videos, voice_segs, out_path, workdir)
    log["out"] = out_path
    return log


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
