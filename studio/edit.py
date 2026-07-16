"""Montage layer — turn raw scene clips into a polished short-form video.

Quality comes from EDITING, not more generation:
- real word-level karaoke captions (edge-tts WordBoundary timing) — the #1 retention
  lever for Shorts/Reels/TikTok;
- crossfade transitions between scenes (xfade) instead of hard cuts;
- optional music bed ducked under the narration.

Everything uses the bundled imageio-ffmpeg binary (libass + xfade verified), so it
runs the same locally and on the server. Functions degrade gracefully.
"""
import os, re, asyncio, subprocess
from studio import ffbin

FF = ffbin.resolve()
W, H = 720, 1280


# ---------- timed narration (real word boundaries) ----------

def tts_timed(text: str, out_mp3: str, voice: str = None, rate: str = "+8%"):
    """Synthesize narration AND capture per-word timings via edge-tts WordBoundary.
    Returns (duration_seconds, [(word, start_s, end_s), ...]). Falls back to even
    spacing if no boundaries are emitted."""
    # Pluggable backend: Yandex SpeechKit (no word boundaries -> proportional timing).
    if os.getenv("TTS_BACKEND", "edge").lower() == "yandex":
        from studio import tts_yandex
        tts_yandex.synth(text, out_mp3, voice=os.getenv("YANDEX_VOICE", "alena"),
                         emotion=os.getenv("YANDEX_EMOTION", "neutral"),
                         speed=float(os.getenv("YANDEX_SPEED", "1.05")))
        dur = _duration(out_mp3)
        # precise word timings via forced alignment (whisper); fall back to proportional
        if os.getenv("FORCE_ALIGN", "1") != "0":
            try:
                from studio import align
                aligned = align.align_known(out_mp3, text)
                if aligned:
                    return dur, aligned
            except Exception:
                pass
        toks = text.split()
        weights = [len(t) + 1 for t in toks]
        tot = sum(weights) or 1
        acc, words = 0.0, []
        for tok, wgt in zip(toks, weights):
            end = acc + dur * wgt / tot
            words.append([tok, acc, end]); acc = end
        return dur, words
    import edge_tts
    voice = voice or os.getenv("TTS_VOICE", "ru-RU-DmitryNeural")
    word_b, sent_b = [], []

    async def _run():
        comm = edge_tts.Communicate(text, voice, rate=rate)
        with open(out_mp3, "wb") as f:
            async for ch in comm.stream():
                t = ch.get("type")
                if t == "audio":
                    f.write(ch["data"])
                elif t == "WordBoundary":
                    s = ch["offset"] / 1e7
                    word_b.append([ch["text"], s, s + ch["duration"] / 1e7])
                elif t == "SentenceBoundary":
                    s = ch["offset"] / 1e7
                    sent_b.append([ch["text"], s, s + ch["duration"] / 1e7])
    import time
    last = None
    for attempt in range(4):                       # edge-tts intermittently returns no audio
        word_b.clear(); sent_b.clear()
        try:
            asyncio.run(_run())
            if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0:
                break
        except Exception as e:
            last = e
        time.sleep(1.2 * (attempt + 1))
    else:
        raise RuntimeError(f"edge-tts no audio after retries: {last}")

    dur = _duration(out_mp3)
    if word_b:
        return dur, word_b
    # Expand real sentence timings into words, weighted by word length (natural).
    words = []
    if sent_b:
        for stext, ss, se in sent_b:
            toks = stext.split()
            if not toks:
                continue
            weights = [len(t) + 1 for t in toks]
            tot = sum(weights)
            span = max(0.01, se - ss)
            acc = ss
            for tok, wgt in zip(toks, weights):
                w_end = acc + span * wgt / tot
                words.append([tok, acc, w_end])
                acc = w_end
        return dur, words
    # Last-resort: split whole text evenly.
    toks = text.split()
    step = dur / max(1, len(toks))
    return dur, [[t, i * step, (i + 1) * step] for i, t in enumerate(toks)]


def _duration(path: str) -> float:
    o = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", o)
    return float(m[1]) * 3600 + float(m[2]) * 60 + float(m[3]) if m else 0.0


# ---------- karaoke captions (ASS) ----------

def _ass_time(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def static_ass(items: list, out_ass: str, font: str = "DejaVu Sans", fontsize: int = 52):
    """One caption line per scene (no word highlight). items = [(text, start_s, end_s)]."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{font},{fontsize},&H00FFFFFF,&H000FB4FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for text, s, e in items:
        if e <= s:
            e = s + 0.5
        lines.append(f"Dialogue: 0,{_ass_time(s)},{_ass_time(e)},Base,,0,0,0,,{_esc(text).upper()}")
    with open(out_ass, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")
    return out_ass


def karaoke_ass(words: list, out_ass: str, group: int = 3,
                font: str = "DejaVu Sans", fontsize: int = 58):
    """Write an ASS file that pops words in groups, highlighting the active word.
    `words` = [(text, start_s, end_s), ...] over the WHOLE video timeline."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{font},{fontsize},&H00FFFFFF,&H000FB4FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,260,1
Style: Hi,{font},{fontsize},&H000FB4FF,&H000FB4FF,&H00101010,&H64000000,-1,0,0,0,108,108,0,0,1,4,2,2,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    # Build phrase-aware groups: break on a pause (scene cut / breath), on sentence
    # punctuation, or when the group is full — so captions never spill across a cut
    # and stay in sync with spoken phrases.
    groups, cur = [], []
    GAP = 0.35   # a gap this long means a scene cut or breath -> new caption group
    for idx, (w, ws, we) in enumerate(words):
        cur.append((w, ws, we))
        nxt_start = words[idx + 1][1] if idx + 1 < len(words) else None
        ends_sentence = w.rstrip()[-1:] in ".!?…:;" if w.strip() else False
        pause = (nxt_start is not None and nxt_start - we > GAP)
        if len(cur) >= group or ends_sentence or pause or nxt_start is None:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    # highlight the currently-spoken word within each group
    for chunk in groups:
        c_start = chunk[0][1]
        c_end = chunk[-1][2]
        for j, (w, ws, we) in enumerate(chunk):
            # render this group for the active word's window, highlighting word j
            parts = []
            for k, (w2, _, _) in enumerate(chunk):
                txt = _esc(w2).upper()
                parts.append("{\\c&H0FB4FF&\\fscx112\\fscy112}" + txt + "{\\r}" if k == j else txt)
            text = " ".join(parts)
            seg_start = ws if j > 0 else c_start
            seg_end = we if j < len(chunk) - 1 else c_end
            if seg_end <= seg_start:
                seg_end = seg_start + 0.12
            lines.append(f"Dialogue: 0,{_ass_time(seg_start)},{_ass_time(seg_end)},Base,,0,0,0,,{text}")
    with open(out_ass, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")
    return out_ass


def trim(raw_clip: str, seconds: float, out: str):
    """Scale/crop a raw clip to vertical frame and trim to length (no caption, no audio)."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    subprocess.run([FF, "-y", "-i", raw_clip, "-t", f"{seconds:.2f}", "-vf", vf,
                    "-an", "-r", "30", "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-pix_fmt", "yuv420p", out],
                   capture_output=True)
    return out


# ---------- transitions ----------

def xfade_stitch(clips: list, out: str, trans: float = 0.4, transition: str = "fade"):
    """Concatenate scene clips with crossfade transitions (no audio; video only)."""
    if len(clips) == 1:
        subprocess.run([FF, "-y", "-i", clips[0], "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-pix_fmt",
                        "yuv420p", "-r", "30", out], capture_output=True)
        return out
    durs = [_duration(c) for c in clips]
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    # build chained xfade; offset accumulates (sum of prior durations - prior transitions)
    fc = []
    prev = "0:v"
    offset = 0.0
    for i in range(1, len(clips)):
        offset += durs[i - 1] - trans
        label = f"x{i}" if i < len(clips) - 1 else "vout"
        fc.append(f"[{prev}][{i}:v]xfade=transition={transition}:duration={trans}:"
                  f"offset={offset:.3f}[{label}]")
        prev = label
    subprocess.run([FF, "-y", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "[vout]", "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-r", "30", out], capture_output=True)
    return out


# ---------- final mux (narration + optional ducked music + burned captions) ----------

def finalize(video_noaudio: str, narration: str, out: str, ass: str = None,
             music: str = None, music_gain_db: float = -18.0, font_dir: str = None):
    """Mux narration over the video, optionally duck a music bed under it and burn
    karaoke captions (ASS). Produces the final short."""
    vf = None
    if ass:
        fd = font_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
        ass_p = ass.replace("\\", "/").replace(":", "\\:")
        vf = f"ass={ass_p}:fontsdir='{os.path.abspath(fd)}'"

    args = [FF, "-y", "-i", video_noaudio, "-i", narration]
    if music and os.path.exists(music):
        args += ["-stream_loop", "-1", "-i", music]
        # lower music, mix with narration, keep narration dominant; end with shortest
        filt = (f"[2:a]volume={music_gain_db}dB[m];[1:a][m]amix=inputs=2:duration=first:"
                f"dropout_transition=2[a]")
        amap = ["-filter_complex", filt, "-map", "0:v:0", "-map", "[a]"]
    else:
        amap = ["-map", "0:v:0", "-map", "1:a:0"]
    if vf:
        args += ["-vf", vf]
    args += [*amap, "-c:v", "libx264", "-threads", "1", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "-shortest", out]
    ffbin.run_checked(args, out_path=out)
    return out
