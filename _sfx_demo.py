"""Render one scenario with the new sound-design layer (no upload). Export audio for A/B."""
import os, sys, time, json, subprocess, re
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from studio import imagegen, qc, story, soundfx
_orig = imagegen.generate_image
imagegen.generate_image = lambda p, o, refs=None, model=None: qc.generate_checked(_orig, p, o, scene=p, refs=refs, tries=3)

def two_pass_loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    p1 = subprocess.run(["ffmpeg","-i",src,"-af",f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json","-f","null","-"],capture_output=True,text=True).stderr
    d = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S).group(0))
    af=(f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
        f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    subprocess.run(["ffmpeg","-y","-i",src,"-af",af,"-c:v","copy","-c:a","aac","-b:a","192k",dst],capture_output=True)

KEY = "silver_needle"
sc = story.load(os.path.join(ROOT, f"scenarios/chayniy/{KEY}.json"))
wd = os.path.join(ROOT, "work", f"{KEY}_sfx_{int(time.time())}")
raw = os.path.join(ROOT,"outputs",f"{KEY}_raw.mp4"); sfx=os.path.join(ROOT,"outputs",f"{KEY}_sfx.mp4"); out=os.path.join(ROOT,"outputs",f"{KEY}_sounddesign.mp4")
music = os.path.join(ROOT,"assets/music/inspired.mp3")
print("rendering:", sc["title"], flush=True)
log = story.build(sc, raw, wd, base_dir=ROOT, draft=True, gen_stills=True, polish=True, music=music, captions=True)
# scene start times from the render log
durs = [s["dur"] for s in log["scenes"]]
cuts, acc = [], 0.0
for d in durs: cuts.append(acc); acc += d
print("cut_times:", [round(c,1) for c in cuts], flush=True)
soundfx.add_sfx(raw, sfx, cuts)
two_pass_loudnorm(sfx, out)
os.remove(raw); os.remove(sfx)
# export audio WAV for Finder A/B
sd_wav = os.path.join(ROOT,"outputs/voice_samples/sounddesign_silver.wav")
subprocess.run(["ffmpeg","-y","-i",out,"-ar","44100","-ac","1",sd_wav],capture_output=True)
print("DONE ->", out, "| audio:", sd_wav, flush=True)
