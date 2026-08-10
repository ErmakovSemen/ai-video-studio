"""Render one fact-checked scenario (QC on) + 2-pass loudnorm -14 + upload public.
Usage: _make.py <key>   where key is a scenarios/chayniy/<key>.json basename."""
import os, sys, time, json, subprocess, re
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from studio import imagegen, qc, story

# QC gate wrap
_orig = imagegen.generate_image
imagegen.generate_image = lambda p, o, refs=None, model=None: qc.generate_checked(_orig, p, o, scene=p, refs=refs, tries=3)

# per-video config: captions on/off + fact-checked metadata
CFG = {
  "bitter_tea": dict(captions=True,
    title="Почему чай горчит — и как это исправить за секунды 🍵",
    desc="Горечь и вязкость чаще всего от слишком горячей воды и долгой заварки: лист отдаёт слишком много катехинов. Дай воде остыть до 70–80 °C и завари короче — тот же чай станет мягким и почти сладким.\n\nЗавари чашку — и почувствуй разницу.",
    tags=["чай","зелёныйчай","завариваниечая","катехины","горечь","лайфхак","чайнаяцеремония"]),
  "golden_tea": dict(captions=False,
    title="Чай, который дороже золота 🍵",
    desc="В горах Уъи на отвесной скале растёт несколько древних кустов Да Хун Пао — им больше 300 лет. Грамм чая с них однажды ценился дороже грамма золота. С 2006 года их лист больше не собирают, а почти весь нынешний Да Хун Пао — побеги от этих кустов.\n\nЗавари чашку — и почувствуй разницу.",
    tags=["чай","ДаХунПао","улун","Китай","редкийчай","Уъи","история"]),
  "milk_tea": dict(captions=True,
    title="Почему англичане льют молоко в чай? 🍵",
    desc="Историки спорят до сих пор. Одна версия: тонкий фарфор раньше мог треснуть от кипятка, и молоко наливали первым, чтобы остудить чашку. Причина попроще — молоко смягчает терпкость крепкого чёрного чая. Так привычка и осталась на века.\n\nЗавари чашку — и почувствуй разницу.",
    tags=["чай","чёрныйчай","Англия","молоко","традиции","история","чайнаяцеремония"]),
  "caffeine_myth": dict(captions=True,
    title="В чае больше кофеина, чем в кофе? 🍵",
    desc="В сухом чайном листе кофеина по весу больше, чем в кофейном зерне. Но на чашку чая берут лишь щепотку листа, а кофе — заметно больше, поэтому в чашке кофе кофеина обычно в 2–3 раза больше. А ещё в чае есть L-теанин — он делает бодрость мягкой, без резкого скачка.\n\nЗавари чашку — и почувствуй разницу.",
    tags=["чай","кофеин","кофе","Lтеанин","наука","миф","бодрость"]),
  "teabag": dict(captions=True,
    title="Чай в пакетике: что там на самом деле 🍵",
    desc="Внутри пакетика часто фэннингс — мельчайшая крошка, что остаётся от крупного листа. Она заваривается быстро и крепко, но тонкий аромат уходит первым. А немало пакетиков ещё и запаяны пластиком, который в кипятке отдаёт микрочастицы. Крупный лист в чайнике — и вкуснее, и чище.\n\nЗавари чашку — и почувствуй разницу.",
    tags=["чай","чайвпакетиках","фэннингс","микропластик","качество","рассыпнойчай"]),
  "origin_legend": dict(captions=False,
    title="5000 лет назад чай открыли случайно 🍵",
    desc="По преданию, почти пять тысяч лет назад китайский правитель Шэнь Нун кипятил воду в тени дерева. Ветер сорвал несколько листьев — и они упали прямо в котёл. Вода потемнела и запахла, он попробовал и не смог оторваться. Так, если верить легенде, и родился чай.\n\nЗавари чашку — и почувствуй разницу.",
    tags=["чай","ШэньНун","легенда","Китай","история","происхождениечая"]),
}

def two_pass_loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    p1 = subprocess.run(["ffmpeg","-i",src,"-af",
        f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json","-f","null","-"],
        capture_output=True, text=True).stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S)
    d = json.loads(m.group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={d['input_i']}:"
          f"measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:"
          f"measured_thresh={d['input_thresh']}:offset={d['target_offset']}:linear=true")
    subprocess.run(["ffmpeg","-y","-i",src,"-af",af,"-c:v","copy","-c:a","aac","-b:a","192k",dst],
                   capture_output=True)

def main(key):
    cfg = CFG[key]
    sc = story.load(os.path.join(ROOT, f"scenarios/chayniy/{key}.json"))
    wd = os.path.join(ROOT, "work", f"{key}_{int(time.time())}")
    raw = os.path.join(ROOT, "outputs", f"{key}_raw.mp4")
    out = os.path.join(ROOT, "outputs", f"{key}.mp4")
    music = os.path.join(ROOT, "assets/music/inspired.mp3")
    print(f"== {key} | captions={cfg['captions']} | {sc['title']}", flush=True)
    story.build(sc, raw, wd, base_dir=ROOT, draft=True, gen_stills=True,
                polish=True, music=music, captions=cfg["captions"])
    two_pass_loudnorm(raw, out); os.remove(raw)
    dur = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nk=1:nw=1",out],capture_output=True,text=True).stdout.strip()
    print(f"   rendered {os.path.getsize(out)//1024}kb {dur}s", flush=True)
    # upload
    tok = json.load(open(os.path.join(ROOT, "yt_token.json")))
    os.environ.update(YT_CLIENT_ID=tok["client_id"], YT_CLIENT_SECRET=tok["client_secret"],
                      YT_REFRESH_TOKEN=tok["refresh_token"])
    from publish.youtube import YouTubePublisher
    from publish.base import VideoMeta
    meta = VideoMeta(title=cfg["title"][:100], description=cfg["desc"], tags=cfg["tags"],
                     category_id="27", privacy="public", made_for_kids=False)
    res = YouTubePublisher().publish(out, meta)
    print(f"   URL: {res['url']}", flush=True)
    # sync a card onto the project board (✅ Опубликовано)
    try:
        from studio import boardsync
        ok = boardsync.add_card("chayniy_content", "posted", {
            "id": f"cli_{key}",
            "title": sc["title"],
            "desc": f"{res['url']}\nсубтитры: {'да' if cfg['captions'] else 'нет'}",
            "video": res["url"],
            "scenario": f"scenarios/chayniy/{key}.json",
            "tags": ["published", "cli", "youtube"],
        }, message=f"board: posted {key}")
        print(f"   board: {'synced' if ok else 'skip (no GH_TOKEN)'}", flush=True)
    except Exception as e:
        print(f"   board: error {e}", flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
