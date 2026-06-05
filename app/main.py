"""AI Video Studio — content-factory UI backend.
Pick/edit a scenario -> render (free draft or final) -> preview -> download / post to TG.
"""
import os, uuid, json, time, threading, urllib.request
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from studio import story, imagegen, video, compose
from publish import registry as publishers, VideoMeta

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"; OUT.mkdir(exist_ok=True)
WORK = ROOT / "work"; WORK.mkdir(exist_ok=True)
SCEN = ROOT / "scenarios"; SCEN.mkdir(exist_ok=True)
ASSETS = ROOT / "assets"
TG_TOKEN = os.getenv("AGT_TG_BOT_TOKEN", "")
TG_CHANNEL = os.getenv("TG_CHANNEL", "@PrometeyApp")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")

app = FastAPI(title="AI Video Studio")

# --- access protection (the UI spends OpenRouter credits + posts to TG) ---
import base64, secrets
from fastapi.responses import Response
STUDIO_USER = os.getenv("STUDIO_USER", "admin")
STUDIO_PASS = os.getenv("STUDIO_PASS", "")  # if unset -> open (local dev)


@app.middleware("http")
async def _auth(request, call_next):
    if STUDIO_PASS:
        hdr = request.headers.get("authorization", "")
        ok = False
        if hdr.startswith("Basic "):
            try:
                u, p = base64.b64decode(hdr[6:]).decode().split(":", 1)
                ok = secrets.compare_digest(u, STUDIO_USER) and secrets.compare_digest(p, STUDIO_PASS)
            except Exception:
                ok = False
        if not ok:
            return Response("Auth required", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="studio"'})
    return await call_next(request)


app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")
JOBS: dict[str, dict] = {}


def _credits():
    if not OR_KEY:
        return None
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://openrouter.ai/api/v1/credits",
            headers={"Authorization": f"Bearer {OR_KEY}"}), timeout=20)
        d = json.load(r).get("data", {})
        return round(float(d.get("total_credits", 0)) - float(d.get("total_usage", 0)), 2)
    except Exception:
        return None


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {"video_model": video.VIDEO_MODEL, "image_model": imagegen.IMAGE_MODEL,
            "tg_ready": bool(TG_TOKEN), "channel": TG_CHANNEL, "credits": _credits()}


@app.get("/api/scenarios")
def scenarios():
    out = []
    for p in sorted(SCEN.glob("*.json")):
        try:
            out.append({"name": p.stem, "title": json.loads(p.read_text(encoding="utf-8")).get("title", p.stem)})
        except Exception:
            out.append({"name": p.stem, "title": p.stem})
    return out


@app.get("/api/scenarios/{name}")
def get_scenario(name: str):
    p = SCEN / f"{name}.json"
    if not p.exists():
        raise HTTPException(404, "not found")
    return json.loads(p.read_text(encoding="utf-8"))


@app.post("/api/scenarios/{name}")
def save_scenario(name: str, body: str = Form(...)):
    try:
        data = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid json: {e}")
    safe = "".join(c for c in name if c.isalnum() or c in "-_")[:40] or "scenario"
    (SCEN / f"{safe}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": safe}


def _run(jid: str, scenario: dict, draft: bool, polish: bool = True, music: str = None):
    out = str(OUT / f"{jid}.mp4")
    wd = str(WORK / jid)
    try:
        log = story.build(scenario, out, wd, base_dir=str(ROOT), draft=draft,
                          polish=polish, music=music)
        JOBS[jid].update(status="done", info=log, video=f"/outputs/{jid}.mp4")
    except Exception as e:
        import traceback; traceback.print_exc()
        JOBS[jid].update(status="error", error=str(e)[:300])


@app.post("/api/render")
def render(body: str = Form(...), draft: bool = Form(True),
           polish: bool = Form(True), music: str = Form("")):
    try:
        scenario = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid scenario json: {e}")
    if not scenario.get("scenes"):
        raise HTTPException(400, "scenario has no scenes")
    music_path = str(ASSETS / "music" / music) if music else None
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = {"status": "running"}
    threading.Thread(target=_run, args=(jid, scenario, draft, polish, music_path),
                     daemon=True).start()
    return {"job_id": jid, "draft": draft, "polish": polish, "scenes": len(scenario["scenes"])}


@app.get("/api/music")
def music_list():
    md = ASSETS / "music"
    if not md.exists():
        return []
    return [p.name for p in sorted(md.glob("*.mp3")) + sorted(md.glob("*.m4a"))]


@app.get("/api/jobs/{jid}")
def job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, "no job")
    return JOBS[jid]


@app.post("/api/image")
def gen_image(prompt: str = Form(...), ref: str = Form("")):
    jid = uuid.uuid4().hex[:10]
    out = str(OUT / f"img_{jid}.png")
    refs = [str(ASSETS / ref)] if ref else []
    try:
        imagegen.generate_image(prompt, out, refs)
        return {"image": f"/outputs/img_{jid}.png"}
    except Exception as e:
        raise HTTPException(500, str(e)[:200])


@app.get("/api/assets")
def assets():
    if not ASSETS.exists():
        return []
    return [str(p.relative_to(ASSETS)) for p in ASSETS.rglob("*.png")]


@app.get("/api/publishers")
def list_publishers():
    return publishers.status()


@app.post("/api/publish")
def publish_video(job_id: str = Form(...), platform: str = Form(...),
                  title: str = Form(...), description: str = Form(""),
                  tags: str = Form(""), privacy: str = Form("public")):
    j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(400, "job not ready")
    path = str(OUT / f"{job_id}.mp4")
    if not os.path.exists(path):
        raise HTTPException(404, "video file missing")
    try:
        pub = publishers.get(platform)
    except KeyError:
        raise HTTPException(400, f"unknown platform: {platform}")
    if not pub.configured():
        raise HTTPException(400, f"{platform} not configured (missing: {', '.join(pub.needs)})")
    meta = VideoMeta(title=title, description=description,
                     tags=[t.strip() for t in tags.split(",") if t.strip()],
                     privacy=privacy)
    try:
        return pub.publish(path, meta)
    except Exception as e:
        raise HTTPException(500, f"{platform}: {str(e)[:300]}")


@app.post("/api/post-tg")
def post_tg(job_id: str = Form(...), caption: str = Form("")):
    if not TG_TOKEN:
        raise HTTPException(400, "TG token not set")
    j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(400, "job not ready")
    path = str(OUT / f"{job_id}.mp4")
    b = "----b" + uuid.uuid4().hex
    def part(n, v):
        return (f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n').encode()
    body = part("chat_id", TG_CHANNEL) + part("caption", caption) + part("supports_streaming", "true")
    body += (f'--{b}\r\nContent-Disposition: form-data; name="video"; filename="v.mp4"\r\n'
             f'Content-Type: video/mp4\r\n\r\n').encode() + open(path, "rb").read() + b"\r\n"
    body += (f'--{b}--\r\n').encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=180)
        d = json.load(r)
        return {"ok": d.get("ok"), "message_id": d.get("result", {}).get("message_id")}
    except Exception as e:
        raise HTTPException(500, f"tg: {e}")
