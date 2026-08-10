"""POC: enrich a talking-head clip with B-roll cutaways (under the words) + karaoke captions.
whisper -> director plan -> generate images -> timed full-frame cutaways with fades -> captions."""
import os, sys, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from studio import imagegen, edit
FF = edit.FF
SRC = "/Users/Semen.Ermakov/Downloads/IMG_3765.MOV"
WAV = "/tmp/clip.wav"

STYLE = ("clean modern editorial illustration, soft muted colors, minimal, tasteful, "
         "vertical 9:16 composition")
# director plan: (start, end, concept, prompt) — placed right as the concept is spoken
PLAN = [
    (8.0, 11.2, "insomnia",  f"a tired man lying awake in bed at night, unable to sleep, moonlight through a window, {STYLE}"),
    (13.0, 16.5, "circadian", f"circadian rhythm concept: a clock merged with a rising sun and a moon, a 24-hour day-and-night cycle, {STYLE}"),
    (24.5, 27.6, "doctor",    f"a friendly doctor in a white coat calmly talking with a patient in a bright clinic, {STYLE}"),
    (37.3, 41.0, "fertility", f"a clean educational medical diagram of sperm cells swimming toward an egg cell, scientific textbook style, {STYLE}"),
    (44.0, 48.2, "latenight", f"a man lying in bed very late at night staring at a glowing phone screen in the dark, disrupted sleep, {STYLE}"),
]

os.makedirs("/tmp/broll", exist_ok=True)
imgs = []
for i, (s, e, label, prompt) in enumerate(PLAN):
    p = f"/tmp/broll/{i}_{label}.png"
    if not os.path.exists(p):
        print("gen", label, flush=True)
        imagegen.generate_image(prompt, p)
    imgs.append(p)

# word timings for karaoke captions (spontaneous speech -> ASR words are the transcript)
from faster_whisper import WhisperModel
mdl = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = mdl.transcribe(WAV, language="ru", word_timestamps=True)
words = []
for sg in segs:
    for w in (sg.words or []):
        words.append([w.word.strip(), float(w.start), float(w.end)])
print("words:", len(words), flush=True)

# --- pass 1: B-roll cutaways with fades ---
inputs = ["-i", SRC]
for p in imgs:
    inputs += ["-loop", "1", "-i", p]
fc = []
for i, (s, e, _, _) in enumerate(PLAN):
    idx = i + 1
    fc.append(f"[{idx}:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
              f"format=rgba,fade=t=in:st={s}:d=0.3:alpha=1,fade=t=out:st={e-0.3}:d=0.3:alpha=1[b{i}]")
prev = "0:v"
for i, (s, e, _, _) in enumerate(PLAN):
    fc.append(f"[{prev}][b{i}]overlay=0:0:enable='between(t,{s},{e})'[v{i}]")
    prev = f"v{i}"
tmp = "/tmp/enriched_broll.mp4"
r = subprocess.run([FF, "-y", *inputs, "-filter_complex", ";".join(fc),
                    "-map", f"[{prev}]", "-map", "0:a", "-c:a", "aac",
                    "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-shortest", tmp],
                   capture_output=True, text=True)
if not os.path.exists(tmp):
    print("PASS1 FAIL:", r.stderr[-600:]); sys.exit(1)

# --- pass 2: karaoke captions ---
ass = "/tmp/enrich.ass"; edit.karaoke_ass(words, ass, group=3)
out = os.path.join(ROOT, "outputs", "enriched_demo.mp4")
ass_p = ass.replace("\\", "/").replace(":", "\\:")
fontsdir = os.path.join(ROOT, "assets", "fonts")
r2 = subprocess.run([FF, "-y", "-i", tmp, "-vf", f"ass={ass_p}:fontsdir='{fontsdir}'",
                     "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", out],
                    capture_output=True, text=True)
print("DONE ->", out if os.path.exists(out) else "FAIL "+r2.stderr[-400:], flush=True)
