"""Render one scenario once, publish 3 UNLISTED sound variants (blind A/B for a poll)."""
import os, sys, time, json, subprocess, re
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from studio import imagegen, qc, story, soundfx
_orig = imagegen.generate_image
imagegen.generate_image = lambda p, o, refs=None, model=None: qc.generate_checked(_orig, p, o, scene=p, refs=refs, tries=3)

def loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    p1 = subprocess.run(["ffmpeg","-i",src,"-af",f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json","-f","null","-"],capture_output=True,text=True).stderr
    d = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S).group(0))
    af=(f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
        f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    subprocess.run(["ffmpeg","-y","-i",src,"-af",af,"-c:v","copy","-c:a","aac","-b:a","192k",dst],capture_output=True)

KEY="teh_tarik"
TITLE="Зачем чай наливают с высоты вытянутой руки 🍵"
DESC="Тех-тарик — «тянутый чай». Челлендж: какой звук лучше? #Shorts"
sc=story.load(os.path.join(ROOT,f"scenarios/chayniy/{KEY}.json"))
wd=os.path.join(ROOT,"work",f"{KEY}_ab_{int(time.time())}")
raw=os.path.join(ROOT,"outputs",f"{KEY}_abraw.mp4")
music=os.path.join(ROOT,"assets/music/inspired.mp3")
print("rendering once:", sc["title"], flush=True)
log=story.build(sc,raw,wd,base_dir=ROOT,draft=True,gen_stills=True,polish=True,music=music,captions=True)
durs=[s["dur"] for s in log["scenes"]]; cuts=[]; acc=0.0
for d in durs: cuts.append(acc); acc+=d

variants=[]
# V1 baseline (music+voice only)
v1=os.path.join(ROOT,"outputs",f"{KEY}_v1.mp4"); loudnorm(raw,v1); variants.append(("V1 — только музыка",v1))
# V2 bell only
t2=os.path.join(ROOT,"outputs",f"{KEY}_v2s.mp4"); soundfx.add_sfx(raw,t2,cuts,bell=True,whoosh=False)
v2=os.path.join(ROOT,"outputs",f"{KEY}_v2.mp4"); loudnorm(t2,v2); os.remove(t2); variants.append(("V2 — гонг на хуке",v2))
# V3 bell + whooshes
t3=os.path.join(ROOT,"outputs",f"{KEY}_v3s.mp4"); soundfx.add_sfx(raw,t3,cuts,bell=True,whoosh=True)
v3=os.path.join(ROOT,"outputs",f"{KEY}_v3.mp4"); loudnorm(t3,v3); os.remove(t3); variants.append(("V3 — гонг + вжухи",v3))
os.remove(raw)

tok=json.load(open(os.path.join(ROOT,"yt_token.json")))
os.environ.update(YT_CLIENT_ID=tok["client_id"],YT_CLIENT_SECRET=tok["client_secret"],YT_REFRESH_TOKEN=tok["refresh_token"])
from publish.youtube import YouTubePublisher
from publish.base import VideoMeta
pub=YouTubePublisher()
for label,path in variants:
    res=pub.publish(path, VideoMeta(title=TITLE[:100],description=DESC,
        tags=["чай","техтарик","shorts"],category_id="27",privacy="unlisted",made_for_kids=False))
    print(f"{label}: {res['url']}", flush=True)
