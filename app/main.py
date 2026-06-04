"""AI Video Studio — FastAPI backend.
UI: upload image + description -> generate video -> download / autopost.
"""
import os, uuid, asyncio, threading, json, urllib.request, mimetypes
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app import pipeline

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"; OUT.mkdir(exist_ok=True)
WORK = ROOT / "work"; WORK.mkdir(exist_ok=True)
TG_TOKEN = os.getenv("AGT_TG_BOT_TOKEN", "")
TG_CHANNEL = os.getenv("TG_CHANNEL", "@PrometeyApp")

app = FastAPI(title="AI Video Studio")
app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")

JOBS: dict[str, dict] = {}


def _run_job(jid: str, description: str, image_path: str | None, narration: str | None):
    out_path = str(OUT / f"{jid}.mp4")
    wd = str(WORK / jid); os.makedirs(wd, exist_ok=True)
    try:
        info = asyncio.run(pipeline.generate(description, image_path, narration, out_path, wd))
        JOBS[jid].update(status="done", info=info, video=f"/outputs/{jid}.mp4")
    except Exception as e:
        import traceback; traceback.print_exc()
        JOBS[jid].update(status="error", error=str(e))


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {"mode": pipeline.mode(), "fal": bool(pipeline.FAL_KEY),
            "tg_ready": bool(TG_TOKEN), "channel": TG_CHANNEL}


@app.post("/api/generate")
async def generate(description: str = Form(...), narration: str = Form(""),
                   image: UploadFile | None = File(None)):
    if not description.strip():
        raise HTTPException(400, "description required")
    jid = uuid.uuid4().hex[:12]
    image_path = None
    if image is not None:
        ext = os.path.splitext(image.filename or "")[1] or ".png"
        image_path = str(WORK / f"{jid}_in{ext}")
        with open(image_path, "wb") as f:
            f.write(await image.read())
    JOBS[jid] = {"status": "running", "info": {}}
    threading.Thread(target=_run_job, args=(jid, description, image_path, narration or None),
                     daemon=True).start()
    return {"job_id": jid, "mode": pipeline.mode()}


@app.get("/api/jobs/{jid}")
def job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, "no job")
    return JOBS[jid]


@app.post("/api/post-tg")
def post_tg(job_id: str = Form(...), caption: str = Form("")):
    if not TG_TOKEN:
        raise HTTPException(400, "TG token not configured")
    j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(400, "job not ready")
    path = str(OUT / f"{job_id}.mp4")
    boundary = "----b" + uuid.uuid4().hex
    body = b""
    def part(name, val):
        return (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n').encode()
    body += part("chat_id", TG_CHANNEL)
    body += part("caption", caption)
    body += part("supports_streaming", "true")
    with open(path, "rb") as f:
        data = f.read()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="v.mp4"\r\n'
             f'Content-Type: video/mp4\r\n\r\n').encode() + data + b"\r\n"
    body += (f'--{boundary}--\r\n').encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        r = urllib.request.urlopen(req, timeout=180)
        d = json.load(r)
        return {"ok": d.get("ok"), "message_id": d.get("result", {}).get("message_id")}
    except Exception as e:
        raise HTTPException(500, f"tg error: {e}")
