"""Yandex SpeechKit TTS backend (v1 synthesize). RU-native voices, RU-friendly billing.

Auth: an API key for a service account with role `ai.speechkit-tts.user`.
Set YANDEX_API_KEY (the key string). No folderId needed with Api-Key auth.

Premium RU voices (support emotions): alena, jane, omazh, filipp, ermil, zahar, dasha,
julia, lera, masha, marina, alexander, kirill, anton. Emotions: neutral|good|evil.
"""
import os, subprocess, urllib.request, urllib.parse

API_KEY = os.getenv("YANDEX_API_KEY", "")
URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


def synth(text: str, out_path: str, voice: str = "alena", emotion: str = "neutral",
          speed: float = 1.05, api_key: str | None = None) -> str:
    """Synthesize `text` to `out_path` (wav or mp3, by extension). Returns out_path."""
    key = api_key or API_KEY
    if not key:
        raise RuntimeError("YANDEX_API_KEY not set")
    data = urllib.parse.urlencode({
        "text": text, "lang": "ru-RU", "voice": voice, "emotion": emotion,
        "speed": f"{speed}", "format": "oggopus",
    }).encode()
    req = urllib.request.Request(URL, data=data, headers={"Authorization": f"Api-Key {key}"})
    audio = urllib.request.urlopen(req, timeout=60).read()
    ogg = out_path + ".ogg"
    with open(ogg, "wb") as f:
        f.write(audio)
    # transcode to the requested container (wav for codec-less players, mp3 otherwise)
    subprocess.run(["ffmpeg", "-y", "-i", ogg, out_path], capture_output=True)
    os.remove(ogg)
    return out_path
