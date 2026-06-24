"""AI Video Studio — content-factory UI backend.
Pick/edit a scenario -> render (free draft or final) -> preview -> download / post to TG.
"""
import os, uuid, json, time, threading, urllib.request
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from studio import story, imagegen, video, compose
from publish import registry as publishers, VideoMeta
from publish import config as pub_config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"; OUT.mkdir(exist_ok=True)
WORK = ROOT / "work"; WORK.mkdir(exist_ok=True)
SCEN = ROOT / "scenarios"; SCEN.mkdir(exist_ok=True)
ASSETS = ROOT / "assets"
PROJECTS = ROOT / "projects"; PROJECTS.mkdir(exist_ok=True)
TG_TOKEN = os.getenv("AGT_TG_BOT_TOKEN", "")
TG_CHANNEL = os.getenv("TG_CHANNEL", "@PrometeyApp")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")

app = FastAPI(title="AI Video Studio")

# --- access protection: session-cookie login (Basic-Auth kept as fallback) ---
import base64, secrets, hmac, hashlib, time
from fastapi.responses import Response, RedirectResponse
STUDIO_USER = os.getenv("STUDIO_USER", "admin")
STUDIO_PASS = os.getenv("STUDIO_PASS", "")  # if unset -> open (local dev)
_SECRET = (os.getenv("APP_SECRET") or (STUDIO_PASS or "dev") + "::prometey-session").encode()
_MAXAGE = 60 * 60 * 24 * 30  # 30 days
PUBLIC_PATHS = {"/login", "/api/login", "/favicon.ico", "/landing", "/terms", "/privacy"}


def _make_session() -> str:
    msg = f"v1.{int(time.time())}"
    sig = hmac.new(_SECRET, msg.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{msg}.{sig}"


def _valid_session(tok: str) -> bool:
    try:
        v, ts, sig = tok.split(".")
        expect = hmac.new(_SECRET, f"{v}.{ts}".encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(sig, expect) and (time.time() - int(ts)) < _MAXAGE
    except Exception:
        return False


def _basic_ok(request) -> bool:
    hdr = request.headers.get("authorization", "")
    if hdr.startswith("Basic "):
        try:
            u, p = base64.b64decode(hdr[6:]).decode().split(":", 1)
            return secrets.compare_digest(u, STUDIO_USER) and secrets.compare_digest(p, STUDIO_PASS)
        except Exception:
            return False
    return False


@app.middleware("http")
async def _auth(request, call_next):
    if not STUDIO_PASS:                       # open in local dev
        return await call_next(request)
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static") or path.startswith("/assets"):
        return await call_next(request)
    tok = request.cookies.get("sid", "")
    if (tok and _valid_session(tok)) or _basic_ok(request):
        return await call_next(request)
    if path.startswith("/api/") or path.startswith("/outputs"):
        return Response("auth required", status_code=401)
    return RedirectResponse("/login")


def _static(name):
    return (Path(__file__).parent / "static" / name).read_text(encoding="utf-8")


@app.get("/landing", response_class=HTMLResponse)
def landing_page():
    return _static("landing.html")


@app.get("/terms", response_class=HTMLResponse)
def terms_page():
    return _static("terms.html")


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page():
    return _static("privacy.html")


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return _static("login.html")


@app.post("/api/login")
def do_login(username: str = Form(""), password: str = Form(...)):
    user_ok = (not username) or secrets.compare_digest(username, STUDIO_USER)
    if user_ok and STUDIO_PASS and secrets.compare_digest(password, STUDIO_PASS):
        resp = RedirectResponse("/cabinet", status_code=303)
        resp.set_cookie("sid", _make_session(), httponly=True, samesite="lax", max_age=_MAXAGE)
        return resp
    return RedirectResponse("/login?e=1", status_code=303)


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("sid")
    return resp


app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")
MEDIA = ROOT / "media"; MEDIA.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA)), name="media")
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


@app.get("/")
def root():
    return RedirectResponse("/cabinet")


@app.get("/studio", response_class=HTMLResponse)
def studio():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


KANBANS = {"board", "content"}   # whitelist of board files


def _board_html():
    return (Path(__file__).parent / "static" / "board.html").read_text(encoding="utf-8")


@app.get("/cabinet", response_class=HTMLResponse)
def cabinet_page():
    return (Path(__file__).parent / "static" / "cabinet.html").read_text(encoding="utf-8")


@app.get("/connect/{platform}", response_class=HTMLResponse)
def connect_page(platform: str):
    return (Path(__file__).parent / "static" / "connect.html").read_text(encoding="utf-8")


@app.get("/board", response_class=HTMLResponse)
def board_page():
    return _board_html()


@app.get("/content", response_class=HTMLResponse)
def content_page():
    return _board_html()


@app.get("/api/kanban/{name}")
def get_kanban(name: str):
    if name not in KANBANS:
        raise HTTPException(404, "no such board")
    # Prefer the durable GitHub copy so agent results (and cross-host edits) show up.
    from studio import boardsync
    remote = boardsync.pull(name)
    if remote is not None:
        try:
            (ROOT / f"{name}.json").write_text(
                json.dumps(remote, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return remote
    p = ROOT / f"{name}.json"
    if not p.exists():
        return {"title": name, "columns": []}
    return json.loads(p.read_text(encoding="utf-8"))


@app.post("/api/kanban/{name}")
def save_kanban(name: str, body: str = Form(...)):
    if name not in KANBANS:
        raise HTTPException(404, "no such board")
    try:
        data = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid json: {e}")
    import datetime
    data["updated"] = datetime.date.today().isoformat()
    (ROOT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    from studio import boardsync
    synced = boardsync.push(name, data, message=f"board: {name} update from page")
    return {"saved": True, "updated": data["updated"], "synced": synced}


# back-compat aliases
@app.get("/api/board")
def get_board():
    return get_kanban("board")


@app.get("/api/health")
def health():
    from studio import higgsfield
    return {"video_provider": video.VIDEO_PROVIDER, "video_model": video.VIDEO_MODEL,
            "higgsfield_ready": higgsfield.configured(), "higgsfield_model": higgsfield.MODEL,
            "image_model": imagegen.IMAGE_MODEL,
            "tg_ready": bool(TG_TOKEN), "channel": TG_CHANNEL, "credits": _credits()}


@app.get("/api/higgsfield/models")
def higgsfield_models():
    from studio import higgsfield
    return {
        "ready": higgsfield.configured(),
        "models": [
            {"id": k, **v}
            for k, v in higgsfield.MODELS.items()
        ],
        "default": higgsfield.MODEL_PATH,
    }


def _load_project(slug: str) -> dict:
    p = PROJECTS / slug / "project.json"
    if not p.exists():
        raise HTTPException(404, f"project not found: {slug}")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/projects")
def list_projects():
    out = []
    for d in sorted(PROJECTS.iterdir()):
        pf = d / "project.json"
        if pf.exists():
            try:
                out.append(json.loads(pf.read_text(encoding="utf-8")))
            except Exception:
                pass
    out.sort(key=lambda p: p.get("order", 99))
    return out


@app.get("/api/projects/{slug}")
def get_project(slug: str):
    return _load_project(slug)


@app.post("/api/projects/{slug}")
def save_project(slug: str, body: str = Form(...)):
    safe = "".join(c for c in slug if c.isalnum() or c in "-_")[:40]
    if not safe:
        raise HTTPException(400, "bad slug")
    try:
        data = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid json: {e}")
    data["id"] = safe
    d = PROJECTS / safe; d.mkdir(exist_ok=True)
    (d / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True}


@app.get("/api/scenarios")
def scenarios(project: str = ""):
    if project:
        scen_dir = SCEN / project
        scen_dir.mkdir(exist_ok=True)
    else:
        scen_dir = SCEN
    out = []
    for p in sorted(scen_dir.glob("*.json")):
        try:
            out.append({"name": p.stem, "title": json.loads(p.read_text(encoding="utf-8")).get("title", p.stem),
                        "project": project or ""})
        except Exception:
            out.append({"name": p.stem, "title": p.stem, "project": project or ""})
    return out


def _scen_path(name: str, project: str = "") -> Path:
    """Resolve scenario file path, optionally scoped to a project subdir."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_")[:80]
    if project:
        safe_proj = "".join(c for c in project if c.isalnum() or c in "-_")[:40]
        d = SCEN / safe_proj; d.mkdir(exist_ok=True)
        return d / f"{safe_name}.json"
    return SCEN / f"{safe_name}.json"


@app.get("/api/scenarios/{name}")
def get_scenario(name: str, project: str = ""):
    p = _scen_path(name, project)
    if not p.exists():
        # fallback: look in root scenarios dir
        p2 = SCEN / f"{name}.json"
        if p2.exists():
            p = p2
        else:
            raise HTTPException(404, "not found")
    return json.loads(p.read_text(encoding="utf-8"))


@app.post("/api/scenarios/{name}")
def save_scenario(name: str, body: str = Form(...), project: str = Form("")):
    try:
        data = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid json: {e}")
    p = _scen_path(name, project)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": p.stem}


def _run(jid: str, scenario: dict, draft: bool, polish: bool = True, music: str = None,
         gen_stills: bool = False, stills_dir: str = None, hf_model_path: str = None):
    out = str(OUT / f"{jid}.mp4")
    wd = str(WORK / jid)
    try:
        log = story.build(scenario, out, wd, base_dir=str(ROOT), draft=draft,
                          polish=polish, music=music, gen_stills=gen_stills,
                          stills_dir=stills_dir, model_path=hf_model_path)
        from studio.host import upload_best_effort
        url = upload_best_effort(out)          # durable mirror so the agent can fetch it
        JOBS[jid].update(status="done", info=log, video=f"/outputs/{jid}.mp4", url=url)
    except Exception as e:
        import traceback; traceback.print_exc()
        JOBS[jid].update(status="error", error=str(e)[:300])


@app.post("/api/render")
def render(body: str = Form(...), draft: bool = Form(True), polish: bool = Form(True),
           music: str = Form(""), gen_stills: bool = Form(False), stills: str = Form(""),
           hf_model: str = Form("")):
    try:
        scenario = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid scenario json: {e}")
    if not scenario.get("scenes"):
        raise HTTPException(400, "scenario has no scenes")
    # Prefer pre-baked scene stills (free, fast, greece-level) over per-scene Gemini.
    slug = "".join(c for c in stills if c.isalnum() or c in "-_")[:60]
    sdir = ROOT / "assets" / "scenes" / slug if slug else None
    has_baked = bool(sdir and sdir.is_dir() and any(p.name.startswith("scene") for p in sdir.iterdir()))
    if has_baked:
        gen_stills = False                         # don't pay for Gemini when stills are committed
    # Default to the ducked music bed for parity with autopost quality.
    if music:
        music_path = str(ASSETS / "music" / music)
    else:
        default_bed = ASSETS / "music" / "inspired.mp3"
        music_path = str(default_bed) if default_bed.exists() else None
    # Resolve Higgsfield model path from model id or raw path
    from studio import higgsfield as hf_mod
    hf_model_path = None
    if hf_model:
        m = hf_mod.MODELS.get(hf_model)
        hf_model_path = m["path"] if m else (hf_model if hf_model.startswith("/") else None)
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = {"status": "running"}
    threading.Thread(target=_run, args=(jid, scenario, draft, polish, music_path, gen_stills,
                                        str(sdir) if has_baked else None, hf_model_path),
                     daemon=True).start()
    return {"job_id": jid, "draft": draft, "polish": polish, "scenes": len(scenario["scenes"]),
            "baked_stills": has_baked, "hf_model": hf_model or "default"}


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


@app.post("/api/upload")
async def upload_asset(file: UploadFile = File(...)):
    """Загрузить сырьё (видео/фото) для монтажа -> /media/uploads/..."""
    up = MEDIA / "uploads"; up.mkdir(exist_ok=True)
    ext = (os.path.splitext(file.filename or "")[1] or ".bin")[:8]
    name = f"{uuid.uuid4().hex[:12]}{ext}"
    data = await file.read()
    (up / name).write_bytes(data)
    kind = "video" if ext.lower().lstrip(".") in ("mp4", "mov", "webm", "mkv", "avi") else "image"
    from studio.host import upload_best_effort
    url = upload_best_effort(str(up / name), filename=name)   # durable mirror for the agent
    return {"path": f"/media/uploads/{name}", "name": file.filename, "kind": kind, "url": url}


def _resolve_media(p: str):
    if p.startswith("/media/"):
        return MEDIA / p[len("/media/"):]
    if p.startswith("/outputs/"):
        return OUT / p[len("/outputs/"):]
    return None


@app.post("/api/ai_montage")
def api_ai_montage(assets: str = Form(...), prompt: str = Form(...)):
    """ИИ-монтаж из сырья: список ассетов (/media|/outputs) + промт -> монтаж."""
    try:
        paths = json.loads(assets)
    except Exception:
        raise HTTPException(400, "assets must be JSON list")
    fs = []
    for p in paths:
        r = _resolve_media(p)
        if r and r.exists():
            fs.append(str(r))
    if not fs:
        raise HTTPException(400, "нет валидных ассетов")
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = {"status": "running"}

    def _run():
        try:
            from studio import ai_montage
            res = ai_montage.ai_montage(fs, prompt, str(OUT / f"{jid}.mp4"), str(WORK / jid))
            from studio.host import upload_best_effort
            url = upload_best_effort(str(OUT / f"{jid}.mp4"))
            JOBS[jid].update(status="done", info={"segments": res["segments"], "duration": res["duration"], "plan": res["plan"]}, video=f"/outputs/{jid}.mp4", url=url)
        except Exception as e:
            import traceback; traceback.print_exc()
            JOBS[jid].update(status="error", error=str(e)[:300])
    threading.Thread(target=_run, args=(), daemon=True).start()
    return {"job_id": jid}


@app.post("/api/publish_file")
def publish_file(video: str = Form(...), title: str = Form(...), description: str = Form("")):
    """Залить файл (из /outputs, /media или durable URL) во все подключённые соцсети."""
    if video.startswith(("http://", "https://")):
        # durable-ссылка (catbox и т.п.) — скачиваем во временный файл и постим
        from studio.host import fetch
        path = OUT / f"pub_{uuid.uuid4().hex[:10]}.mp4"
        OUT.mkdir(exist_ok=True)
        try:
            fetch(video, str(path))
        except Exception as e:
            raise HTTPException(400, f"не скачать видео по URL: {str(e)[:160]}")
    elif video.startswith("/outputs/"):
        path = OUT / video[len("/outputs/"):]
    elif video.startswith("/media/"):
        path = MEDIA / video[len("/media/"):]
    else:
        raise HTTPException(400, "bad video path")
    if not path.exists():
        raise HTTPException(404, "video file missing")
    meta = VideoMeta(title=title[:100], description=description, privacy="public")
    results = []
    for p in publishers.publishers():
        if p.configured():
            try:
                results.append(p.publish(str(path), meta))
            except Exception as e:
                results.append({"platform": p.name, "error": str(e)[:200]})
    if not results:
        raise HTTPException(400, "нет подключённых платформ (Подключения)")
    return {"results": results}


@app.post("/api/ai_edit")
def ai_edit(scenario: str = Form(...)):
    """ИИ-монтажёр: LLM улучшает субтитры сценария -> render-ready *_ai.json + правки."""
    safe = "".join(c for c in scenario if c.isalnum() or c in "-_")[:60]
    p = SCEN / f"{safe}.json"
    if not p.exists():
        raise HTTPException(404, f"сценарий не найден: {safe}")
    try:
        from studio import ai_editor
        res = ai_editor.ai_edit(str(p))
        return {"ok": True, "scenario": os.path.basename(res["scenario"]), "edits": res["edits"]}
    except Exception as e:
        raise HTTPException(500, f"ai_edit: {str(e)[:300]}")


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


@app.get("/api/settings")
def get_settings():
    """Per-platform connection state for the Settings UI (values masked)."""
    out = []
    for p in publishers.publishers():
        stored = pub_config.get_platform(p.name)
        fields = []
        for f in p.fields:
            val = stored.get(f["key"], "")
            fields.append({**f, "set": bool(val),
                           "preview": ("•••• " + val[-4:]) if (val and f.get("secret")) else val})
        out.append({"name": p.name, "label": p.label, "configured": p.configured(),
                    "setup_hint": p.setup_hint, "fields": fields})
    return out


@app.post("/api/settings/{platform}")
def save_settings(platform: str, body: str = Form(...)):
    try:
        values = json.loads(body)
    except Exception as e:
        raise HTTPException(400, f"invalid json: {e}")
    try:
        publishers.get(platform)
    except KeyError:
        raise HTTPException(400, f"unknown platform: {platform}")
    pub_config.save(platform, {k: v for k, v in values.items() if isinstance(v, str)})
    p = publishers.get(platform)
    return {"saved": platform, "configured": p.configured()}


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
