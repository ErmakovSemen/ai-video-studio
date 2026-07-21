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
            "-o", "ConnectTimeout=15"]


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


def run_montage_job(input_paths, prompt, out_path, progress=None, captions=False,
                    style="minimalist Asian ink wash on parchment", insert_mode="fullscreen",
                    aspect="source", max_tries=3):
    """Полный цикл: поднять воркер -> прогнать монтаж -> забрать out.mp4 -> погасить."""
    def prog(m, pct):
        if progress:
            progress(m, pct)

    image_id = os.getenv("TW_WORKER_IMAGE_ID", tw.WORKER_IMAGE_ID)
    if not image_id:
        raise RuntimeError("TW_WORKER_IMAGE_ID не задан — golden-образ не собран")

    reap_stale()
    name = f"prometey-worker-{uuid.uuid4().hex[:8]}"
    prog("поднимаю рендер-воркер", 3)
    sid = tw.create_server(name, from_image=image_id)
    try:
        # IPv4 воркеру НЕ нужен: OpenRouter за Cloudflare доступен по IPv6, а контейнер
        # монтажа запускаем с --network host, чтобы он брал IPv6-egress хоста. Это ещё и
        # обходит анти-фрод Timeweb (attach IPv4 требует держать ~6000₽ на балансе).
        ip = tw.wait_ready(sid, timeout=600)
        _wait_ssh(ip)
        prog("воркер готов, заливаю задачу", 10)

        # свежий код (перекрывает запечённый в образе) + окружение
        subprocess.run(["rsync", "-a", "-e", f"ssh {' '.join(SSH_OPTS)}",
                        "--exclude", "data", "--exclude", ".git", "--exclude", "work",
                        "--exclude", "outputs", f"{CODE_DIR}/", f"root@{_b(ip)}:/opt/prometey/"],
                       check=True, timeout=300)
        _ssh(ip, "mkdir -p /opt/job/inputs")
        job = {"inputs": [], "prompt": prompt, "captions": captions, "style": style,
               "insert_mode": insert_mode, "aspect": aspect, "max_tries": max_tries}
        for i, p in enumerate(input_paths):
            ext = os.path.splitext(p)[1] or ".mp4"
            rp = f"/opt/job/inputs/in{i}{ext}"
            _scp(p, f"root@{_b(ip)}:{rp}", timeout=1200)
            job["inputs"].append(rp.replace("/opt/job", "/job"))
        # job.json
        jf = f"/tmp/job_{sid}.json"
        json.dump(job, open(jf, "w"))
        _scp(jf, f"root@{_b(ip)}:/opt/job/job.json")
        os.remove(jf)

        prog("монтирую (это самый долгий этап)", 15)
        run = ("docker run -d --name montage --network host "
               "-v /opt/prometey:/app -v /opt/models:/root/.cache/huggingface "
               "-v /opt/job:/job --env-file /opt/prometey/.env.prod "
               "prometey-app python3 -m studio.worker.run_montage /job")
        r = _ssh(ip, run)
        if r.returncode != 0:
            raise RuntimeError(f"не удалось запустить контейнер монтажа: {r.stderr[-400:]}")

        # ждём завершения контейнера, транслируя прогресс
        while True:
            time.sleep(12)
            st = _ssh(ip, "docker inspect -f '{{.State.Running}} {{.State.ExitCode}}' montage 2>/dev/null || echo 'gone 1'")
            parts = st.stdout.strip().split()
            running = parts[0] if parts else "gone"
            pj = _ssh(ip, "cat /opt/job/progress.json 2>/dev/null || echo '{}'").stdout.strip()
            try:
                pd = json.loads(pj)
                if "stage" in pd:
                    # маппим прогресс монтажа в диапазон 15..92
                    inner = pd.get("progress", 0)
                    outer = 15 + int(max(0, min(100, inner)) * 0.77)
                    prog(pd["stage"], outer)
            except Exception:
                pass
            if running != "true":
                exit_code = parts[1] if len(parts) > 1 else "1"
                break

        res = _ssh(ip, "cat /opt/job/result.json 2>/dev/null || echo '{}'").stdout.strip()
        try:
            result = json.loads(res)
        except Exception:
            result = {}
        if not result.get("ok"):
            logs = _ssh(ip, "docker logs --tail 40 montage 2>&1 | tail -40").stdout.strip()
            raise RuntimeError(f"монтаж на воркере упал: {result.get('error', 'unknown')} "
                               f"(exit {exit_code})\n--- worker logs ---\n{logs}")

        prog("забираю результат", 94)
        rr = _scp(f"root@{_b(ip)}:/opt/job/out.mp4", out_path, timeout=1200)
        if rr.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) < 1000:
            raise RuntimeError(f"не удалось забрать результат: {rr.stderr[-300:]}")
        prog("готово", 100)
        return result.get("result", {})
    finally:
        try:
            tw.destroy_server(sid)
        except Exception:
            pass
