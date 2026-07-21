"""On-demand рендер-воркер: под тяжёлый монтаж поднимаем мощный сервер из golden-образа
через Timeweb API, гоняем задачу, забираем результат и ГАСИМ воркер. Платим только за минуты.

Запускается на веб-узле (у него есть Timeweb-токен, SSH-ключ воркера и IPv6-доступ).
Всё в try/finally — воркер уничтожается даже при ошибке, чтобы не платить за зомби.
"""
import json
import os
import subprocess
import time
import uuid

from studio.worker import tw

KEY = os.getenv("TW_WORKER_SSH_KEY", "/root/.ssh/prometey_worker")
CODE_DIR = os.getenv("PROMETEY_CODE_DIR", "/opt/prometey")
ENV_FILE = os.getenv("PROMETEY_ENV_FILE", "/opt/prometey/.env.prod")
SSH_OPTS = ["-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=6",
            "-o", "BatchMode=yes"]


def _ssh(ip, cmd, timeout=120):
    r = subprocess.run(["ssh", *SSH_OPTS, f"root@{ip}", cmd], capture_output=True, text=True, timeout=timeout)
    return r


def _scp(src, dst, timeout=600, recursive=False):
    args = ["scp", *SSH_OPTS]
    if recursive:
        args.append("-r")
    args += [src, dst]
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _b(ip):
    """IPv6 в скобках для scp."""
    return f"[{ip}]" if ":" in ip else ip


def _ship_verified(ip, local, remote, timeout=600, tries=4):
    """scp файла на воркер с проверкой, что он реально долетел (IPv6-scp иногда рвётся)."""
    want = os.path.getsize(local)
    for attempt in range(tries):
        _scp(local, f"root@{_b(ip)}:{remote}", timeout=timeout)
        got = _ssh(ip, f"stat -c%s {remote} 2>/dev/null || echo 0").stdout.strip()
        if got.isdigit() and int(got) == want:
            return
        time.sleep(5)
    raise RuntimeError(f"не удалось доставить {os.path.basename(local)} на воркер ({want} байт)")


def _wait_ssh(ip, timeout=180, poll=6):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _ssh(ip, "echo ok", timeout=20).stdout.strip() == "ok":
            return True
        time.sleep(poll)
    raise TimeoutError(f"воркер {ip} не пускает по SSH за {timeout}с")


def reap_stale(prefix="prometey-worker-", max_age_s=3 * 3600):
    """Подчистить забытые воркеры (защита от зомби-биллинга)."""
    now = time.time()
    for s in tw.list_servers():
        if not str(s.get("name", "")).startswith(prefix):
            continue
        try:
            created = s.get("created_at", "")
            # если не парсится — сносим по факту префикса (наши эфемерные)
            age = max_age_s + 1
            if created:
                import datetime
                age = now - datetime.datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
            if age > max_age_s:
                tw.destroy_server(s["id"])
        except Exception:
            pass


def _provision(prog):
    """Поднять воркер из golden-образа, дождаться SSH, залить свежий код. -> (sid, ip)."""
    image_id = os.getenv("TW_WORKER_IMAGE_ID", tw.WORKER_IMAGE_ID)
    if not image_id:
        raise RuntimeError("TW_WORKER_IMAGE_ID не задан — golden-образ не собран")
    reap_stale()
    name = f"prometey-worker-{uuid.uuid4().hex[:8]}"
    prog("поднимаю рендер-воркер", 3)
    sid = tw.create_server(name, from_image=image_id)
    # IPv4 воркеру НЕ нужен: OpenRouter за Cloudflare доступен по IPv6, а контейнер
    # запускаем с --network host (IPv6-egress хоста). Это обходит и анти-фрод Timeweb.
    ip = tw.wait_ready(sid, timeout=600)
    _wait_ssh(ip)
    prog("воркер готов, заливаю задачу", 10)
    # свежий код (перекрывает запечённый в образе) + окружение; rsync докачивает при обрыве
    for attempt in range(3):
        rr = subprocess.run(["rsync", "-a", "--timeout=60", "-e", f"ssh {' '.join(SSH_OPTS)}",
                             "--exclude", "data", "--exclude", ".git", "--exclude", "work",
                             "--exclude", "outputs", f"{CODE_DIR}/", f"root@{_b(ip)}:/opt/prometey/"],
                            capture_output=True, text=True, timeout=400)
        if rr.returncode == 0:
            break
        if attempt == 2:
            raise RuntimeError(f"rsync кода на воркер не удался: {rr.stderr[-300:]}")
        time.sleep(5)
    return sid, ip


def _run_and_wait(ip, module, prog, prog_lo=15, prog_hi=92):
    """Запустить контейнер `module` (studio.worker.<module>) детачем и ждать завершения,
    транслируя прогресс. Возвращает result-dict из /opt/job/result.json.
    Устойчиво к транзиентным обрывам IPv6-SSH: «готово» только при явном Running=false."""
    run = (f"docker rm -f job 2>/dev/null; docker run -d --name job --network host "
           "-v /opt/prometey:/app -v /opt/models:/root/.cache/huggingface "
           "-v /opt/job:/job --env-file /opt/prometey/.env.prod "
           f"prometey-app python3 -m studio.worker.{module} /job")
    started = False
    for attempt in range(3):
        r = _ssh(ip, run)
        chk = _ssh(ip, "docker inspect -f '{{.State.Running}}' job 2>/dev/null || echo no")
        if r.returncode == 0 or chk.stdout.strip() == "true":
            started = True
            break
        time.sleep(8)
    if not started:
        raise RuntimeError(f"не удалось запустить контейнер задачи: {r.stderr[-400:]}")

    deadline = time.time() + int(os.getenv("JOB_MAX_SECONDS", "5400"))
    while time.time() < deadline:
        time.sleep(12)
        st = _ssh(ip, "echo START; docker inspect -f '{{.State.Running}}|{{.State.ExitCode}}' job 2>/dev/null; echo END")
        out = st.stdout
        if "START" not in out or "END" not in out:
            continue                                       # ssh оборвался — просто ждём
        body = out.split("START", 1)[1].split("END", 1)[0].strip()
        if "|" not in body:
            continue
        running, _code = body.split("|", 1)
        pj = _ssh(ip, "cat /opt/job/progress.json 2>/dev/null || echo '{}'").stdout.strip()
        try:
            pd = json.loads(pj)
            if "stage" in pd:
                inner = pd.get("progress", 0)
                outer = prog_lo + int(max(0, min(100, inner)) * (prog_hi - prog_lo) / 100)
                prog(pd["stage"], outer)
        except Exception:
            pass
        if running.strip() == "false":
            break

    result = {}
    for _ in range(5):
        res = _ssh(ip, "echo START; cat /opt/job/result.json 2>/dev/null; echo END").stdout
        if "START" in res and "END" in res:
            try:
                result = json.loads(res.split("START", 1)[1].split("END", 1)[0].strip())
                break
            except Exception:
                pass
        time.sleep(5)
    if not result.get("ok"):
        logs = _ssh(ip, "docker logs --tail 40 job 2>&1 | tail -40").stdout.strip()
        raise RuntimeError(f"задача на воркере упала: {result.get('error', 'unknown')}"
                           f"\n--- worker logs ---\n{logs}")
    return result.get("result", {})


def _fetch(ip, remote, local, timeout=1200, tries=4):
    """Скачать файл с воркера с проверкой размера и ретраями."""
    want = _ssh(ip, f"stat -c%s {remote} 2>/dev/null || echo 0").stdout.strip()
    want = int(want) if want.isdigit() else 0
    for _ in range(tries):
        rr = _scp(f"root@{_b(ip)}:{remote}", local, timeout=timeout)
        if os.path.exists(local) and os.path.getsize(local) >= max(1000, want):
            return
        time.sleep(5)
    raise RuntimeError(f"не удалось забрать {os.path.basename(remote)} ({want} байт): {rr.stderr[-200:]}")


def run_montage_job(input_paths, prompt, out_path, progress=None, captions=False,
                    style="minimalist Asian ink wash on parchment", insert_mode="fullscreen",
                    aspect="source", max_tries=3):
    """Нейромонтаж на эфемерном воркере: поднять -> смонтировать -> забрать out.mp4 -> погасить."""
    def prog(m, pct):
        if progress:
            progress(m, pct)
    sid, ip = _provision(prog)
    try:
        _ssh(ip, "mkdir -p /opt/job/inputs")
        job = {"inputs": [], "prompt": prompt, "captions": captions, "style": style,
               "insert_mode": insert_mode, "aspect": aspect, "max_tries": max_tries}
        for i, p in enumerate(input_paths):
            ext = os.path.splitext(p)[1] or ".mp4"
            rp = f"/opt/job/inputs/in{i}{ext}"
            _ship_verified(ip, p, rp, timeout=1800)
            job["inputs"].append(rp.replace("/opt/job", "/job"))
        jf = f"/tmp/job_{sid}.json"; json.dump(job, open(jf, "w"))
        _ship_verified(ip, jf, "/opt/job/job.json"); os.remove(jf)

        prog("монтирую (это самый долгий этап)", 15)
        result = _run_and_wait(ip, "run_montage", prog)
        prog("забираю результат", 94)
        _fetch(ip, "/opt/job/out.mp4", out_path)
        prog("готово", 100)
        return result
    finally:
        try:
            tw.destroy_server(sid)
        except Exception:
            pass


def run_clip_job(video_path, out_dir, progress=None, n=5, captions=True, min_s=20, max_s=60):
    """Нарезка длинного видео на Shorts на воркере: поднять -> нарезать -> забрать N роликов."""
    def prog(m, pct):
        if progress:
            progress(m, pct)
    os.makedirs(out_dir, exist_ok=True)
    sid, ip = _provision(prog)
    try:
        _ssh(ip, "mkdir -p /opt/job/inputs /opt/job/out")
        ext = os.path.splitext(video_path)[1] or ".mp4"
        rp = f"/opt/job/inputs/in0{ext}"
        prog("заливаю видео на воркер", 12)
        _ship_verified(ip, video_path, rp, timeout=3600)   # видео может быть большим
        job = {"video": rp.replace("/opt/job", "/job"), "n": n, "captions": captions,
               "min_s": min_s, "max_s": max_s}
        jf = f"/tmp/job_{sid}.json"; json.dump(job, open(jf, "w"))
        _ship_verified(ip, jf, "/opt/job/job.json"); os.remove(jf)

        prog("нарезаю на Shorts (это самый долгий этап)", 15)
        result = _run_and_wait(ip, "run_clip", prog)
        prog("забираю ролики", 94)
        shorts = []
        for s in result.get("shorts", []):
            local = os.path.join(out_dir, s["file"])
            _fetch(ip, f"/opt/job/out/{s['file']}", local)
            s["local"] = local
            shorts.append(s)
        result["shorts"] = shorts
        prog("готово", 100)
        return result
    finally:
        try:
            tw.destroy_server(sid)
        except Exception:
            pass
