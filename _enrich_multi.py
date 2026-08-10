"""POC: multi-clip -> normalize -> stitch with crossfade transitions -> B-roll (no captions)."""
import os, sys, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from studio import edit
FF = edit.FF
SRC = "/Users/Semen.Ermakov/Downloads/IMG_3765.MOV"
W, H, FPS = 720, 1280, 30
XF = 0.6  # crossfade duration

# 1) split into 3 "separate clips" and NORMALIZE each to a common canvas (the real multi-clip crux)
segs = [(0, 18), (18, 18), (36, 16.7)]
paths = []
for i, (ss, d) in enumerate(segs):
    p = f"/tmp/seg{i}.mp4"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}")
    subprocess.run([FF, "-y", "-ss", str(ss), "-t", str(d), "-i", SRC, "-vf", vf,
                    "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "48000", p], capture_output=True)
    paths.append((p, d))

# 2) stitch with xfade (video) + acrossfade (audio)
d0, d1, d2 = paths[0][1], paths[1][1], paths[2][1]
off1 = d0 - XF
off2 = d0 + d1 - 2 * XF          # cumulative length after first xfade minus next overlap
vf = (f"[0:v][1:v]xfade=transition=fade:duration={XF}:offset={off1}[vx1];"
      f"[vx1][2:v]xfade=transition=fade:duration={XF}:offset={off2}[vout];"
      f"[0:a][1:a]acrossfade=d={XF}[ax1];[ax1][2:a]acrossfade=d={XF}[aout]")
stitched = "/tmp/stitched.mp4"
subprocess.run([FF, "-y", "-i", paths[0][0], "-i", paths[1][0], "-i", paths[2][0],
                "-filter_complex", vf, "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", stitched],
               capture_output=True)
tot = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",stitched],
                           capture_output=True, text=True).stdout.strip())
print(f"stitched: {tot:.1f}s (sum was {d0+d1+d2:.1f}s, minus 2 crossfades)", flush=True)

# 3) B-roll cutaways over the stitched timeline (reuse already-generated images), NO captions
broll = [(8.5, 11.3, "/tmp/broll/0_insomnia.png"),
         (22.5, 25.5, "/tmp/broll/2_doctor.png"),
         (36.0, 39.5, "/tmp/broll/3_fertility.png")]
inputs = ["-i", stitched]
for _, _, p in broll:
    inputs += ["-loop", "1", "-i", p]
fc = []
for i, (s, e, _) in enumerate(broll):
    fc.append(f"[{i+1}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"format=rgba,fade=t=in:st={s}:d=0.3:alpha=1,fade=t=out:st={e-0.3}:d=0.3:alpha=1[b{i}]")
prev = "0:v"
for i, (s, e, _) in enumerate(broll):
    fc.append(f"[{prev}][b{i}]overlay=0:0:enable='between(t,{s},{e})'[v{i}]"); prev = f"v{i}"
out = os.path.join(ROOT, "outputs", "multi_enriched_demo.mp4")
subprocess.run([FF, "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-map", "0:a",
                "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-shortest", out],
               capture_output=True)
print("DONE ->", out if os.path.exists(out) else "FAIL", flush=True)
