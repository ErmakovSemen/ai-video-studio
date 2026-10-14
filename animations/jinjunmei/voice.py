"""Озвучка офлайн (RHVoice): каждая фраза синтезируется отдельно и ставится на свой момент сюжета.
Выход: out/voice.wav (48 кГц, моно). Голос: VOICE=<имя> (см. /usr/share/RHVoice/voices)."""
import json, os, pathlib, subprocess, tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

HERE = pathlib.Path(__file__).parent
T = json.loads((HERE / "timing.json").read_text())
VOICE = os.environ.get("VOICE", "aleksandr-hq")
RATE = os.environ.get("RATE", "120")  # темп речи, %
SR = 48000


def real(x):  # время сюжета -> реальное (как в audio.py и scenes.js)
    return x + sum(d for h, d in T["holds"] if x > h)


def synth(text):
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["RHVoice-test", "-p", VOICE, "-r", RATE, "-o", f.name], input=text.encode(), check=True)
        sr, a = wavfile.read(f.name)
    a = a.astype(np.float64) / 32768
    if a.ndim > 1: a = a.mean(1)
    a = resample_poly(a, SR, sr)
    nz = np.flatnonzero(np.abs(a) > 0.01)  # срезаем тишину по краям
    return a[max(0, nz[0] - 480): nz[-1] + 2400] if len(nz) else a


track = np.zeros(int(T["duration"] * SR))
rows, prev_end = [], 0.0
for st, align, text in T["voice"]:
    a = synth(text); dur = len(a) / SR
    t0 = real(st) - (dur if align == "end" else 0)
    flag = " <- НАЛЕЗАЕТ" if t0 < prev_end - 0.05 else ""
    i = int(t0 * SR); track[i:i + len(a)] += a[: len(track) - i]
    rows.append(f"{t0:6.2f}–{t0 + dur:6.2f}  {text}{flag}"); prev_end = t0 + dur
assert prev_end <= T["duration"], "озвучка не влезает в ролик"
(HERE / "out").mkdir(exist_ok=True)
track *= 0.89 / max(1e-9, np.abs(track).max())
wavfile.write(HERE / "out" / "voice.wav", SR, (track * 32767).astype(np.int16))
print(f"voice ({VOICE}):"); print("\n".join(rows))
