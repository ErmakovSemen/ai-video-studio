"""Render one scenario once, publish 3 UNLISTED caption variants (blind A/B for a poll):
V1 no captions | V2 karaoke (word highlight) | V3 static (one line per scene)."""
import os, sys, time, json, subprocess, re
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from studio import imagegen, qc, story, edit
_orig = imagegen.generate_image
imagegen.generate_image = lambda p, o, refs=None, model=None: qc.generate_checked(_orig, p, o, scene=p, refs=refs, tries=3)
FF = edit.FF
FONTSDIR = os.path.join(ROOT, "assets", "fonts")

def loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    p1 = subprocess.run(["ffmpeg","-i",src,"-af",f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json","-f","null","-"],capture_output=True,text=True).stderr
    d = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S).group(0))
    af=(f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
        f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    subprocess.run(["ffmpeg","-y","-i",src,"-af",af,"-c:v","copy","-c:a","aac","-b:a","192k",dst],capture_output=True)

def burn(base, ass_path, dst):
    ass_p = ass_path.replace("\\","/").replace(":","\\:")
    vf = f"ass={ass_p}:fontsdir='{os.path.abspath(FONTSDIR)}'"
    subprocess.run([FF,"-y","-i",base,"-vf",vf,"-c:a","copy","-c:v","libx264","-preset","ultrafast",
                    "-pix_fmt","yuv420p",dst],capture_output=True)

KEY="oriental_beauty"
TITLE="Этот чай вкусный, потому что его покусали жучки 🍵"
DESC="Восточная красавица — улун, вкус которого создают насекомые. Челлендж: как удобнее с субтитрами? #Shorts"
sc=story.load(os.path.join(ROOT,f"scenarios/chayniy/{KEY}.json"))
wd=os.path.join(ROOT,"work",f"{KEY}_cab_{int(time.time())}")
raw=os.path.join(ROOT,"outputs",f"{KEY}_cabraw.mp4")
music=os.path.join(ROOT,"assets/music/inspired.mp3")
print("rendering once (no captions):", sc["title"], flush=True)
log=story.build(sc,raw,wd,base_dir=ROOT,draft=True,gen_stills=True,polish=True,music=music,captions=False)
words=log["words"]; durs=[s["dur"] for s in log["scenes"]]
cuts=[]; acc=0.0
for d in durs: cuts.append(acc); acc+=d

# normalize the shared base audio once
base=os.path.join(ROOT,"outputs",f"{KEY}_base.mp4"); loudnorm(raw, base); os.remove(raw)

variants=[]
# V1 no captions
v1=os.path.join(ROOT,"outputs",f"{KEY}_c1.mp4"); subprocess.run(["ffmpeg","-y","-i",base,"-c","copy",v1],capture_output=True); variants.append(("V1 — без субтитров",v1))
# V2 karaoke
ass_k=os.path.join(wd,"k.ass"); edit.karaoke_ass(words, ass_k, group=3)
v2=os.path.join(ROOT,"outputs",f"{KEY}_c2.mp4"); burn(base, ass_k, v2); variants.append(("V2 — караоке (по словам)",v2))
# V3 static one-line-per-scene
items=[(sc["scenes"][i].get("caption",""), cuts[i]+0.1, cuts[i]+durs[i]-0.25) for i in range(len(durs))]
ass_s=os.path.join(wd,"s.ass"); edit.static_ass(items, ass_s)
v3=os.path.join(ROOT,"outputs",f"{KEY}_c3.mp4"); burn(base, ass_s, v3); variants.append(("V3 — статичные (по сцене)",v3))

tok=json.load(open(os.path.join(ROOT,"yt_token.json")))
os.environ.update(YT_CLIENT_ID=tok["client_id"],YT_CLIENT_SECRET=tok["client_secret"],YT_REFRESH_TOKEN=tok["refresh_token"])
from publish.youtube import YouTubePublisher
from publish.base import VideoMeta
pub=YouTubePublisher()
for label,path in variants:
    res=pub.publish(path, VideoMeta(title=TITLE[:100],description=DESC,tags=["чай","улун","shorts"],
        category_id="27",privacy="unlisted",made_for_kids=False))
    print(f"{label}: {res['url']}", flush=True)
