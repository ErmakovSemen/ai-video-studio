"""Звук синтезом под константы timing.json: шорох карандаша, сминание и бросок бумаги, переворот страниц, свиток, гонг, чай, щипки, аккорд.
Без стоков. Выход: out/audio.wav (48 кГц, стерео). Громкость потом нормализуется ffmpeg loudnorm."""
import json, pathlib
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = pathlib.Path(__file__).parent
T = json.loads((HERE / "timing.json").read_text())
SR = 48000
N = int(T["duration"] * SR)
L = np.zeros(N); Rch = np.zeros(N)
rng = np.random.default_rng(2005)


def real(x):  # время сюжета -> реальное (с учётом пауз на чтение, как story() в scenes.js)
    return x + sum(d for h, d in T["holds"] if x > h)


def windows(ws):  # окна рисования режем паузами: во время паузы карандаш молчит
    out = []
    for a, b in ws:
        cuts = [a] + [h for h, _ in T["holds"] if a < h < b] + [b]
        for x0, x1 in zip(cuts, cuts[1:]):
            out.append((real(x0) if x0 == a else x0 + sum(d for h, d in T["holds"] if x0 >= h), real(x1)))
    return out


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2)
    Rch[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)


def env(n, a=0.005, decay=1.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / decay)


def hz(note):  # 'A4' -> Гц
    names = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}
    return 440 * 2 ** ((names[note[0]] + 12 * (int(note[-1]) - 4)) / 12)


def pluck(f, dur=1.6, bright=0.5):  # Карплус-Стронг: щипок струны (гучжэн)
    n = int(dur * SR); p = int(SR / f)
    buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.994 + 0.005 * bright)
    return out * env(n, 0.002, dur * 0.6)


def bell(f, dur=2.5):
    t = np.arange(int(dur * SR)) / SR
    parts = [(1, 1, 1.0), (2.76, 0.4, 0.5), (5.4, 0.2, 0.25), (8.9, 0.1, 0.12)]
    return sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (dur * d)) for m, a, d in parts) * np.minimum(1, t / 0.003)


# 1) гул: холодный до поворота, тёплый после
t = np.arange(N) / SR
turn = real(T["turn"])
cold = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.4 * t + 0.3) + 0.25 * np.sin(2 * np.pi * 110.7 * t))
warm = (np.sin(2 * np.pi * 49 * t) + 0.6 * np.sin(2 * np.pi * 73.4 * t) + 0.5 * np.sin(2 * np.pi * 61.7 * t) + 0.3 * np.sin(2 * np.pi * 98 * t))
x = np.clip((t - turn + 0.1) / 0.5, 0, 1)
drone = ((1 - x) * cold + x * warm * 1.2) * np.clip(t / 1.5, 0, 1) * np.clip((T["duration"] - t) / 2.0, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * t))
L += drone * 0.055; Rch += drone * 0.055

# 2) шорох карандаша, пока карточка прорисовывается
bp = lambda lo, hi, x: signal.lfilter(*signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band"), x)
scratch = bp(1800, 7000, rng.standard_normal(N))
gate = np.zeros(N)
for a0, a1 in windows(T["draw"]): gate[int(a0 * SR):int(a1 * SR)] = 1
gate = signal.lfilter([1 / 2400], [1, -1 + 1 / 2400], gate)
k = np.floor(t * T["drawRate"]).astype(int)
stroke = rng.uniform(0.35, 1.0, k.max() + 2)[k]
L += scratch * gate * stroke * 0.045; Rch += scratch * gate * stroke * 0.04

# 3) бумага: сминание (треск), бросок (свист), переворот страницы (шелест + хлопок)
def crunch(dur):
    n = int(dur * SR); out_ = np.zeros(n)
    for _ in range(int(dur * 90)):
        i = rng.integers(0, n - 800); m = rng.integers(150, 700)
        out_[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / (m / 4)) * rng.uniform(0.3, 1)
    return bp(900, 7000, out_) * np.sin(np.pi * np.arange(n) / n) ** 0.5
def whoosh(dur, f0=500, f1=2600):
    n = int(dur * SR); src = rng.standard_normal(n); out_ = np.zeros(n)
    for j in range(0, n, 1200):
        fc = f0 + (f1 - f0) * np.sin(np.pi * j / n); out_[j:j + 1200] = bp(fc * 0.7, min(SR / 2 - 100, fc * 1.4), src[j:j + 1200])
    return out_ * np.sin(np.pi * np.arange(n) / n)
for b, kind in zip(T["B"], T["kind"]):
    tb = real(b)
    if kind == "crumple":
        add(crunch(0.5), tb, 0.55, pan=-0.1)
        add(whoosh(0.4), tb + 0.5, 0.45, pan=0.5)
    else:
        add(whoosh(0.5, 1500, 4500), tb + 0.1, 0.35, pan=-0.2)
        ft = np.arange(int(0.2 * SR)) / SR
        add(np.sin(2 * np.pi * 95 * ft) * np.exp(-ft / 0.05) + 0.3 * bp(400, 3000, rng.standard_normal(len(ft))) * np.exp(-ft / 0.02), tb + 0.85, 0.35)

# 4) свиток разворачивается + поворот: гонг
u0, u1 = real(T["unroll"][0]), real(T["unroll"][1])
add(bp(300, 2500, rng.standard_normal(int((u1 - u0) * SR))) * np.linspace(0.3, 1, int((u1 - u0) * SR)), u0, 0.3)
gt = np.arange(int(3.2 * SR)) / SR
gong = sum(a * np.sin(2 * np.pi * 70 * m * gt) * np.exp(-gt / d) for m, a, d in [(1, 1, 2.2), (2.41, 0.6, 1.4), (3.93, 0.4, 0.9), (5.32, 0.25, 0.6)])
add(gong * 0.35 + np.sin(2 * np.pi * (48 + 60 * np.exp(-gt / 0.04)) * gt) * np.exp(-gt / 0.25) * 0.6, u1 - 0.05, 1.0)
st = np.arange(int(0.4 * SR)) / SR
add(np.sin(2 * np.pi * 110 * st) * np.exp(-st / 0.09) + 0.2 * rng.standard_normal(len(st)) * np.exp(-st / 0.02), real(T["stamp"]), 0.5)

# 5) льётся чай
a0, a1 = real(T["pour"][0]) + 0.25, real(T["pour"][1]) - 0.1
n = int((a1 - a0) * SR); tt = np.arange(n) / SR
gurgle = bp(600, 2400, rng.standard_normal(n)) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * tt + 3 * np.sin(2 * np.pi * 1.3 * tt))) * np.clip(tt / 0.1, 0, 1) * np.clip((tt[-1] - tt) / 0.15, 0, 1)
add(gurgle, a0, 0.2, pan=0.2)

# 6) щипки (холодно) и тёплый мотив
for i, tp in enumerate(T["plucks"]):
    add(pluck(hz(["A3", "C4", "E4", "D4", "G3", "A3"][i % 6]), 1.8, 0.2), real(tp), 0.26, pan=-0.3 + 0.1 * i)
for i, tm in enumerate(T["motif"]):
    add(pluck(hz(["G4", "B4", "D5", "E5", "D5", "G5"][i % 6]), 1.6, 0.9), real(tm), 0.28, pan=0.2 - 0.08 * i)

# 7) финальный аккорд
for j, nt in enumerate(["G3", "D4", "G4", "B4"]):
    add(bell(hz(nt), 4.5) * 0.7 + pluck(hz(nt), 4.5, 0.8) * 0.5, real(T["finalChord"]) + 0.08 * j, 0.15)

for d_, g_ in [(0.031, 0.25), (0.047, 0.2), (0.071, 0.15), (0.113, 0.1)]:
    s_ = int(d_ * SR); L[s_:] += Rch[:-s_] * g_; Rch[s_:] += L[:-s_] * g_ * 0.9

fade = np.clip((T["duration"] - t) / 1.0, 0, 1)
mix = np.stack([L * fade, Rch * fade], 1)
mix /= max(1e-9, np.abs(mix).max()) / 0.8
out = HERE / "out"; out.mkdir(exist_ok=True)
wavfile.write(out / "audio_raw.wav", SR, (mix * 32767).astype(np.int16))
print("audio_raw.wav ok", mix.shape)
