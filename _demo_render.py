"""Demo render: render+publish one scenario, print URL. Does NOT touch the board
(so the live UI stays the sole board writer during the manual demo)."""
import os, sys, time, json, subprocess, re
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from studio import imagegen, qc, story

_orig = imagegen.generate_image
imagegen.generate_image = lambda p, o, refs=None, model=None: qc.generate_checked(_orig, p, o, scene=p, refs=refs, tries=3)

KEY = "blooming_tea"
TITLE = "Этот чай расцветает прямо в чашке 🍵🌸"
DESC = ("Связанный (цветущий) чай — пучок чайных листьев с вшитым вручную цветком. "
        "В горячей воде он медленно распускается в маленький подводный сад. "
        "Сначала его смотрят, потом пьют.\n\nЗавари чашку — и почувствуй разницу.")
TAGS = ["чай", "цветущийчай", "связанныйчай", "чайнаяцеремония", "эстетика", "tea"]

def two_pass_loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    p1 = subprocess.run(["ffmpeg","-i",src,"-af",
        f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json","-f","null","-"],
        capture_output=True, text=True).stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S); d = json.loads(m.group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    subprocess.run(["ffmpeg","-y","-i",src,"-af",af,"-c:v","copy","-c:a","aac","-b:a","192k",dst], capture_output=True)

sc = story.load(os.path.join(ROOT, f"scenarios/chayniy/{KEY}.json"))
wd = os.path.join(ROOT, "work", f"{KEY}_{int(time.time())}")
raw = os.path.join(ROOT, "outputs", f"{KEY}_raw.mp4"); out = os.path.join(ROOT, "outputs", f"{KEY}.mp4")
music = os.path.join(ROOT, "assets/music/inspired.mp3")
print("rendering:", sc["title"], flush=True)
story.build(sc, raw, wd, base_dir=ROOT, draft=True, gen_stills=True, polish=True, music=music, captions=True)
two_pass_loudnorm(raw, out); os.remove(raw)
print("rendered", os.path.getsize(out)//1024, "kb", flush=True)
tok = json.load(open(os.path.join(ROOT, "yt_token.json")))
os.environ.update(YT_CLIENT_ID=tok["client_id"], YT_CLIENT_SECRET=tok["client_secret"], YT_REFRESH_TOKEN=tok["refresh_token"])
from publish.youtube import YouTubePublisher
from publish.base import VideoMeta
res = YouTubePublisher().publish(out, VideoMeta(title=TITLE[:100], description=DESC, tags=TAGS,
        category_id="27", privacy="public", made_for_kids=False))
print("URL:", res["url"], flush=True)
