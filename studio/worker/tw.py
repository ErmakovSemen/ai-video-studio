"""Тонкий клиент Timeweb Cloud API для управления жизненным циклом рендер-воркеров.

Только то, что нужно оркестратору: создать сервер (из образа или ОС), дождаться готовности,
узнать IP, погасить, сделать образ. Все секреты — из окружения, ничего не логируем.
"""
import json
import os
import time
import urllib.request
import urllib.error

API = "https://api.timeweb.cloud/api/v1"
TOKEN = os.getenv("TIMEWEB_API_TOKEN", "")

# Дефолты под наш аккаунт (nl-1, Ubuntu 26.04). Переопределяемы через env.
LOCATION = os.getenv("TW_LOCATION", "nl-1")
OS_ID = int(os.getenv("TW_OS_ID", "145"))                 # ubuntu 26.04
WORKER_PRESET = int(os.getenv("TW_WORKER_PRESET", "3348"))  # 4CPU/8GB
SSH_KEY_ID = int(os.getenv("TW_SSH_KEY_ID", "723731"))     # prometey-worker
WORKER_IMAGE_ID = os.getenv("TW_WORKER_IMAGE_ID", "")     # golden image (если собран)


def _req(path, method="GET", body=None, timeout=40):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        raise RuntimeError(f"Timeweb API {method} {path} -> HTTP {e.code}: {detail}")


def create_server(name, preset_id=None, from_image=None, os_id=None):
    """Создать сервер. from_image=image_id грузит golden-образ (быстро), иначе чистую ОС."""
    body = {
        "name": name,
        "preset_id": preset_id or WORKER_PRESET,
        "ssh_keys_ids": [SSH_KEY_ID],
        "bandwidth": int(os.getenv("TW_BANDWIDTH", "1000")),
        "is_ddos_guard": False,
    }
    if from_image:
        body["image_id"] = from_image
    else:
        body["os_id"] = os_id or OS_ID
    r = _req("/servers", method="POST", body=body)
    return r["server"]["id"]


def add_ipv4(server_id):
    """Прицепить публичный IPv4 — нужен воркеру для исходящих запросов (OpenRouter, apt/pip
    внутри Docker). IPv6-only бокс не имеет IPv4-egress, и контейнеры теряют сеть."""
    r = _req(f"/servers/{server_id}/ips", method="POST", body={"type": "ipv4"})
    return r.get("server_ip", {}).get("ip")


def get_server(server_id):
    return _req(f"/servers/{server_id}")["server"]


def server_ip(server_id, prefer="ipv6"):
    """IP сервера. Воркеры IPv6-only, поэтому по умолчанию берём IPv6 (для SSH с веб-узла);
    если его нет — падаем на IPv4."""
    s = get_server(server_id)
    order = [prefer, "ipv4" if prefer == "ipv6" else "ipv6"]
    for want in order:
        for n in s.get("networks", []):
            for ip in n.get("ips", []):
                if ip.get("type") == want:
                    return ip["ip"]
    return None


def wait_ready(server_id, timeout=600, poll=10):
    """Ждём status=on и наличие IP (IPv6 для наших воркеров). Возвращает IP."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = get_server(server_id)
        if s.get("status") == "on":
            ip = server_ip(server_id)
            if ip:
                return ip
        time.sleep(poll)
    raise TimeoutError(f"сервер {server_id} не поднялся за {timeout}с")


def destroy_server(server_id):
    _req(f"/servers/{server_id}", method="DELETE")


def list_servers():
    return _req("/servers").get("servers", [])


def create_image(server_id, name):
    """Снимок диска сервера как переиспользуемый образ (для golden-воркера)."""
    disk_id = None
    s = get_server(server_id)
    for d in s.get("disks", []):
        disk_id = d["id"]
        break
    if not disk_id:
        raise RuntimeError(f"у сервера {server_id} не найден диск")
    r = _req("/images", method="POST", body={"disk_id": disk_id, "name": name})
    return r["image"]["id"]


def get_image(image_id):
    return _req(f"/images/{image_id}")["image"]


def wait_image(image_id, timeout=1200, poll=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        img = get_image(image_id)
        if img.get("status") == "created":
            return img
        if img.get("status") in ("failed", "error"):
            raise RuntimeError(f"образ {image_id} собрался с ошибкой: {img.get('status')}")
        time.sleep(poll)
    raise TimeoutError(f"образ {image_id} не собрался за {timeout}с")
