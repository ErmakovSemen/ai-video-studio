"""Credential store for publishers.

Platforms can be connected from the app's Settings UI (stored in a gitignored
config/credentials.json, mode 600) OR via environment variables. UI value wins,
env is the fallback — so local dev and Render env both keep working.
"""
import os
import json
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "config", "credentials.json")
_lock = threading.Lock()


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get(platform: str, key: str, env: str | None = None, default=None):
    """Resolve a credential: credentials.json[platform][key] -> env var -> default."""
    val = _load().get(platform, {}).get(key)
    if val:
        return val
    if env and os.getenv(env):
        return os.getenv(env)
    return default


def get_platform(platform: str) -> dict:
    return _load().get(platform, {})


def save(platform: str, values: dict) -> None:
    """Merge non-empty values into the platform's stored credentials."""
    with _lock:
        data = _load()
        data.setdefault(platform, {})
        for k, v in values.items():
            if v is not None and v != "":
                data[platform][k] = v
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(PATH, 0o600)
        except Exception:
            pass


def clear(platform: str) -> None:
    with _lock:
        data = _load()
        data.pop(platform, None)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
