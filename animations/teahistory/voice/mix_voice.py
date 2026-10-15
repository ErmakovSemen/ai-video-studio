"""Сведение озвучки с роликом: реплики по главам, фон (эффекты + музыка) приседает под голос.

python3 mix_voice.py --video teahistory.mp4 --bed bed.m4a --clips clips/ --out out.mp4 [--until 12]
clips/<id>.mp3 — реплики из narration.json; отсутствующие пропускаются (удобно для пробы одной главы).
Время реплики: `at` из narration.json или начало главы + offset. Если реплика не влезает до следующей главы,
она чуть ускоряется (до ×1,12), а если и этого мало — начинается раньше, но не раньше начала главы + 0,4 с.
Громкость: каждая реплика к −16 LUFS, фон −4,5 дБ и компрессия по голосу, итог в два прохода к −15 LUFS.
"""
import argparse, json, pathlib, subprocess, tempfile

HERE = pathlib.Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True); ap.add_argument("--bed", required=True)
ap.add_argument("--clips", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--timing", default=str(HERE.parent / "timing.json"))
ap.add_argument("--narration", default=str(HERE / "narration.json"))
ap.add_argument("--until", type=float, default=None, help="обрезать результат (превью)")
a = ap.parse_args()

T = json.loads(pathlib.Path(a.timing).read_text()); N = json.loads(pathlib.Path(a.narration).read_text())
S = {s["id"]: s for s in T["scenes"]}; order = [s["id"] for s in T["scenes"]]
dur = lambda f: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout)

plan = []
for ln in N["lines"]:
    f = pathlib.Path(a.clips) / f"{ln['id']}.mp3"
    if not f.exists(): continue
    if ln["id"] in S:
        i = order.index(ln["id"]); s0 = S[ln["id"]]["start"]
        start = s0 + N["offset"]
        end = T["scenes"][i + 1]["start"] - 0.15 if i + 1 < len(order) else T["duration"] - 0.8
    else:
        s0, start, end = 0.0, ln["at"], ln.get("end", T["cover"] + 1.0)
    d = dur(f); tempo = 1.0
    if start + d > end: tempo = min(1.12, d / max(0.1, end - start))
    if start + d / tempo > end: start = max(s0 + 0.4, end - d / tempo)
    plan.append((f, round(start, 3), round(tempo, 3), round(d / tempo, 2), end))
    print(f"{ln['id']:8s} {start:6.2f}s +{d / tempo:4.1f}s (×{tempo}) до {end:5.2f}s", flush=True)

inputs = ["-i", a.bed]; fc = ["[0:a]aresample=48000,aformat=channel_layouts=stereo,volume=-4.5dB[bed]"]
for k, (f, start, tempo, _, _) in enumerate(plan, 1):
    inputs += ["-i", str(f)]; ms = int(start * 1000)
    fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-2:LRA=7,aresample=48000,"
              f"atempo={tempo},adelay={ms}|{ms}[v{k}]")
vs = "".join(f"[v{k}]" for k in range(1, len(plan) + 1))
fc.append(f"{vs}amix=inputs={len(plan)}:normalize=0:duration=longest,asplit[vo][sc]")
fc.append("[bed][sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[duck]")
fc.append("[duck][vo]amix=inputs=2:normalize=0:duration=first[mix]")

with tempfile.TemporaryDirectory() as tmp:
    raw, norm = f"{tmp}/raw.wav", f"{tmp}/norm.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[mix]", raw], check=True)
    LN = "I=-15:TP=-1.5:LRA=11"
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", f"loudnorm={LN}:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-af",
                    f"loudnorm={LN}:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
                    f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}", "-ar", "48000", norm], check=True)
    cut = ["-t", str(a.until)] if a.until else []
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.video, "-i", norm, *cut, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    r = subprocess.run(["ffmpeg", "-nostats", "-i", a.out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    print("готово:", a.out, "|", " ".join(x.strip() for x in r.splitlines() if x.strip().startswith(("I:", "Peak:"))))
