"""Звук синтезом под константы timing.json: шаги, ветер, чай, гонг, печать, взмах мантии, щипки, аккорд.
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


# 1) гул: до поворота холодная квинта, после — тёплое мажорное трезвучие
t = np.arange(N) / SR
turn = real(T["turn"])
cold = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.4 * t + 0.3) + 0.25 * np.sin(2 * np.pi * 110.7 * t))
warm = (np.sin(2 * np.pi * 49 * t) + 0.6 * np.sin(2 * np.pi * 73.4 * t) + 0.5 * np.sin(2 * np.pi * 61.7 * t) + 0.3 * np.sin(2 * np.pi * 98 * t))
x = np.clip((t - turn + 0.1) / 0.4, 0, 1)
drone = ((1 - x) * cold + x * warm * 1.2) * np.clip(t / 1.5, 0, 1) * np.clip((T["duration"] - t) / 2.0, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * t))
L += drone * 0.055; Rch += drone * 0.055

# 2) ветер: медленно плывущий шум
noise = rng.standard_normal(N)
wind = signal.lfilter(*signal.butter(2, [200 / (SR / 2), 900 / (SR / 2)], btype="band"), noise) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t + 1))
L += wind * 0.02; Rch += wind * 0.018

# 3) шорох карандаша в окнах рисования
scratch = signal.lfilter(*signal.butter(2, [1800 / (SR / 2), 7000 / (SR / 2)], btype="band"), rng.standard_normal(N))
gate = np.zeros(N)
for a0, a1 in windows(T["draw"]): gate[int(a0 * SR):int(a1 * SR)] = 1
gate = signal.lfilter([1 / 2400], [1, -1 + 1 / 2400], gate)
k = np.floor(t * T["drawRate"]).astype(int)
stroke = rng.uniform(0.35, 1.0, k.max() + 2)[k]
L += scratch * gate * stroke * 0.045; Rch += scratch * gate * stroke * 0.04

# 4) шаги: мягкий глухой удар + шорох ткани
for i, ts in enumerate(T["steps"]):
    n = int(0.12 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (70 + 40 * np.exp(-tt / 0.02)) * tt) * np.exp(-tt / 0.04)
    rustle = signal.lfilter(*signal.butter(2, 2500 / (SR / 2), "high"), rng.standard_normal(n)) * np.exp(-tt / 0.03) * 0.25
    add(thud + rustle, real(ts), 0.32, pan=-0.3 + 0.6 * (i % 2))

# 5) падение: глухой удар + шелест
ft = np.arange(int(0.5 * SR)) / SR
add(np.sin(2 * np.pi * 60 * ft) * np.exp(-ft / 0.12) + 0.3 * rng.standard_normal(len(ft)) * np.exp(-ft / 0.05), real(T["fall"] + 0.9), 0.5)

# 6) льётся чай: полосовой шум с «бульканьем»
a0, a1 = real(T["pour"][0]) + 0.15, real(T["pour"][1]) - 0.15
n = int((a1 - a0) * SR); tt = np.arange(n) / SR
gurgle = signal.lfilter(*signal.butter(2, [600 / (SR / 2), 2400 / (SR / 2)], btype="band"), rng.standard_normal(n))
gurgle *= (0.6 + 0.4 * np.sin(2 * np.pi * 11 * tt + 3 * np.sin(2 * np.pi * 1.3 * tt))) * np.clip(tt / 0.1, 0, 1) * np.clip((tt[-1] - tt) / 0.15, 0, 1)
add(gurgle, a0, 0.18, pan=0.2)

# 7) щипки до поворота (минорная пентатоника)
for i, tp in enumerate(T["plucks"]):
    add(pluck(hz(["A3", "C4", "E4", "D4", "G3", "A3"][i % 6]), 1.8, 0.2), real(tp), 0.26, pan=-0.3 + 0.1 * i)

# 8) поворот: гонг + удар; печать
gt = np.arange(int(3.2 * SR)) / SR
gong = sum(a * np.sin(2 * np.pi * 70 * m * gt) * np.exp(-gt / d) for m, a, d in [(1, 1, 2.2), (2.41, 0.6, 1.4), (3.93, 0.4, 0.9), (5.32, 0.25, 0.6)])
thump = np.sin(2 * np.pi * (48 + 60 * np.exp(-gt / 0.04)) * gt) * np.exp(-gt / 0.25)
add(gong * 0.35 + thump * 0.6, turn, 1.0)
st = np.arange(int(0.4 * SR)) / SR
add(np.sin(2 * np.pi * 110 * st) * np.exp(-st / 0.09) + 0.2 * rng.standard_normal(len(st)) * np.exp(-st / 0.02), real(T["stamp"]), 0.5)

# 9) тёплый мотив (мажорная пентатоника)
for i, tm in enumerate(T["motif"]):
    add(pluck(hz(["G4", "B4", "D5", "E5", "D5", "G5"][i % 6]), 1.6, 0.9), real(tm), 0.28, pan=0.2 - 0.08 * i)

# 10) взмах мантии: свист ткани от броска до касания кустов
a0, a1 = real(T["throw"]), real(T["drape"])
n = int((a1 - a0 + 0.3) * SR); tt = np.arange(n) / SR
sw = rng.standard_normal(n); out_ = np.zeros(n); f0 = 400
for j in range(0, n, 2400):
    seg_ = sw[j:j + 2400]; fc = f0 + 2600 * np.sin(np.pi * min(1, j / n))
    out_[j:j + len(seg_)] = signal.lfilter(*signal.butter(2, [fc * 0.7 / (SR / 2), min(0.99, fc * 1.4 / (SR / 2))], btype="band"), seg_)
out_ *= np.sin(np.pi * np.clip(tt / (a1 - a0 + 0.3), 0, 1))
add(out_, a0, 0.35, pan=0.4)
dt = np.arange(int(0.6 * SR)) / SR
add(np.sin(2 * np.pi * 85 * dt) * np.exp(-dt / 0.15) + 0.25 * signal.lfilter(*signal.butter(2, 1200 / (SR / 2)), rng.standard_normal(len(dt))) * np.exp(-dt / 0.1), a1, 0.45, pan=0.4)

# 11) финальный аккорд
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
