"""Composition helpers — voice, captions, scene sync, end-card, stitch.

Recipe fixes from the Icarus pilot:
- each scene clip is trimmed to its narration length (+pad) so audio/video stay in
  sync and the ending doesn't drift;
- captions burned per scene; clean end-card; explicit audio map (use narration,
  not the clip's own audio).
"""
import os, re, subprocess, asyncio, sys
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()


def _resolve_font() -> str:
    env = os.getenv("STUDIO_FONT")
    if env and os.path.exists(env):
        return env
    bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                           "assets", "fonts", "DejaVuSans.ttf")
    if os.path.exists(bundled):
        return os.path.abspath(bundled)
    for p in ("/Library/Fonts/Arial Unicode.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return p
    return "DejaVuSans.ttf"


FONT = _resolve_font()
VOICE = os.getenv("TTS_VOICE", "ru-RU-DmitryNeural")
W, H = 720, 1280


def tts(text: str, out: str):
    """Generate TTS via edge-tts CLI (more reliable than Python API)."""
    import time, shutil
    # Find edge-tts CLI: prefer same venv as current interpreter
    venv_cli = os.path.join(os.path.dirname(sys.executable), "edge-tts")
    cli = venv_cli if os.path.exists(venv_cli) else shutil.which("edge-tts") or "edge-tts"
    last = None
    for attempt in range(5):
        if os.path.exists(out):
            os.remove(out)
        try:
            result = subprocess.run(
                [cli, "--voice", VOICE, "--rate", "+8%", "--text", text, "--write-media", out],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
                return
            last = result.stderr or f"exit {result.returncode}"
        except Exception as e:
            last = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"edge-tts CLI failed after retries: {last}")


def dur(path: str) -> float:
    o = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", o)
    return float(m[1])*3600 + float(m[2])*60 + float(m[3]) if m else 4.0


def silence(out: str, sec: float):
    subprocess.run([FF, "-y", "-f", "lavfi", "-t", f"{sec}", "-i",
                    "anullsrc=r=24000:cl=mono", out], capture_output=True)


def text_card(text: str, out_png: str):
    """A simple branded still for free drafts when there is no image."""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np, textwrap
    y = np.linspace(0, 1, H)[:, None]
    arr = (np.array([26, 19, 33]) * (1 - y) + np.array([9, 9, 13]) * y).astype("uint8")
    img = Image.fromarray(np.repeat(arr[:, None, :], W, axis=1), "RGB")
    d = ImageDraw.Draw(img)
    d.multiline_text((W//2, H//2), textwrap.fill(text, 22),
                     font=ImageFont.truetype(FONT, 52), fill=(240, 240, 245),
                     anchor="mm", align="center", spacing=14)
    img.save(out_png)


def mock_clip(image_path: str | None, fallback_text: str, seconds: float, out: str):
    """Free draft clip: slow Ken-Burns zoom on an image (or a text card)."""
    src = image_path
    tmp = None
    if not src or not os.path.exists(src):
        tmp = out + ".bg.png"; text_card(fallback_text, tmp); src = tmp
    frames = max(2, int(seconds * 30))
    subprocess.run([FF, "-y", "-loop", "1", "-i", src, "-t", f"{seconds:.2f}",
                    "-vf", (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                            f"zoompan=z='min(zoom+0.0009,1.16)':d={frames}:s={W}x{H}:fps=30,format=yuv420p"),
                    "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-an", out], capture_output=True)
    if tmp and os.path.exists(tmp):
        os.remove(tmp)


def _wrap(text: str, width: int = 14) -> str:
    """Greedy word-wrap into lines of ~width chars (drawtext has no auto-wrap)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def burn_hook(clip: str, hook: str, out: str):
    """Burn a bold, high-contrast HOOK line near the top — the first-second grab.

    Big yellow text on a translucent dark box, upper third, persistent for the clip.
    """
    if not hook.strip():
        subprocess.run([FF, "-y", "-i", clip, "-c", "copy", out], capture_output=True)
        return out
    hf = out + ".hook.txt"
    open(hf, "w", encoding="utf-8").write(_wrap(hook.strip().upper()))
    vf = (f"drawtext=textfile='{hf}':fontfile='{FONT}':fontsize=54:fontcolor=0x0AD6FF:"
          f"borderw=6:bordercolor=black:box=1:boxcolor=black@0.45:boxborderw=24:"
          f"line_spacing=12:x=(w-tw)/2:y=170")
    subprocess.run([FF, "-y", "-i", clip, "-vf", vf, "-an", "-r", "30",
                    "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", out], capture_output=True)
    return out


def scene_clip(raw_clip: str, caption: str, seconds: float, out: str):
    """Trim a raw clip to `seconds`, burn a bottom caption, drop its audio."""
    capf = out + ".txt"; open(capf, "w", encoding="utf-8").write(caption)
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"drawtext=textfile='{capf}':fontfile='{FONT}':fontsize=44:fontcolor=white:"
          f"borderw=3:bordercolor=black:x=(w-tw)/2:y=h-300")
    subprocess.run([FF, "-y", "-i", raw_clip, "-t", f"{seconds:.2f}", "-vf", vf,
                    "-an", "-r", "30", "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-pix_fmt", "yuv420p", out],
                   capture_output=True)


def endcard(brand_img: str, title: str, sub: str, seconds: float, out: str):
    from PIL import Image, ImageDraw, ImageFont
    src = Image.open(brand_img).convert("RGB")
    # Cover-crop the artwork to fill the 9:16 frame (same as scene clips): keeps the
    # character proportional, fills edge-to-edge with the real background (no stretch,
    # no seam). Bias the crop slightly upward so feet sit above the bottom banner.
    scale = max(W / src.width, H / src.height)
    nw, nh = round(src.width * scale), round(src.height * scale)
    big = src.resize((nw, nh), Image.LANCZOS)
    left = (nw - W) // 2
    top = min(nh - H, int((nh - H) * 0.30))   # upward bias
    img = big.crop((left, top, left + W, top + H))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H-220, W, H], fill=(10, 12, 16))
    d.text((W//2, H-150), title, font=ImageFont.truetype(FONT, 64),
           fill=(255, 170, 60), anchor="mm")
    d.text((W//2, H-80), sub, font=ImageFont.truetype(FONT, 38),
           fill=(230, 230, 235), anchor="mm")
    p = out + ".png"; img.save(p)
    subprocess.run([FF, "-y", "-loop", "1", "-i", p, "-t", f"{seconds:.2f}",
                    "-vf", "format=yuv420p", "-r", "30", "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-an", out],
                   capture_output=True)


def stitch(scene_videos: list[str], voice_segs: list[str], out: str, workdir: str):
    """Concat scene videos + concat narration, mux narration over video."""
    lst = os.path.join(workdir, "v.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in scene_videos))
    vcat = os.path.join(workdir, "vcat.mp4")
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "30", vcat],
                   capture_output=True)
    ins = []
    for v in voice_segs:
        ins += ["-i", v]
    fc = "".join(f"[{i}:a]" for i in range(len(voice_segs))) + \
         f"concat=n={len(voice_segs)}:v=0:a=1[a]"
    acat = os.path.join(workdir, "acat.m4a")
    subprocess.run([FF, "-y", *ins, "-filter_complex", fc, "-map", "[a]", acat],
                   capture_output=True)
    subprocess.run([FF, "-y", "-i", vcat, "-i", acat, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", out], capture_output=True)
    return out
