"""Звук синтезом под константы timing.json: шорох карандаша, щипки, удар, тики почек, колокола, аккорд.
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
drone = (1 - x) * cold + x * warm * 1.2
drone *= np.clip(t / 1.2, 0, 1) * np.clip((T["duration"] - t) / 1.5, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.17 * t))
L += drone * 0.06; Rch += drone * 0.06

# 2) шорох карандаша в окнах рисования: полосовой шум, пульсирует на двойках (12 рисунков/с)
noise = rng.standard_normal(N)
b, a = signal.butter(2, [1800 / (SR / 2), 7000 / (SR / 2)], btype="band")
scratch = signal.lfilter(b, a, noise)
gate = np.zeros(N)
for a0, a1 in windows(T["draw"]):
    i0, i1 = int(a0 * SR), int(a1 * SR)
    gate[i0:i1] = 1
gate = signal.lfilter([1 / 2400], [1, -1 + 1 / 2400], gate)  # мягкие края
k = np.floor(t * T["drawRate"]).astype(int)
stroke = rng.uniform(0.35, 1.0, k.max() + 2)[k] * (0.6 + 0.4 * np.abs(np.sin(np.pi * (t * T["drawRate"] % 1))))
L += scratch * gate * stroke * 0.05; Rch += scratch * gate * stroke * 0.045

# 3) щипки до поворота (минорная пентатоника, холодно)
for i, tp in enumerate(T["plucks"]):
    add(pluck(hz(["A3", "C4", "E4", "D4", "G3", "A3"][i % 6]), 1.8, 0.2), real(tp), 0.28, pan=-0.3 + 0.12 * i)

# 4) поворот: гонг + удар
gt = np.arange(int(3.2 * SR)) / SR
gong = sum(a * np.sin(2 * np.pi * 70 * m * gt) * np.exp(-gt / d) for m, a, d in [(1, 1, 2.2), (2.41, 0.6, 1.4), (3.93, 0.4, 0.9), (5.32, 0.25, 0.6)])
thump = np.sin(2 * np.pi * (48 + 60 * np.exp(-gt / 0.04)) * gt) * np.exp(-gt / 0.25)
burst = signal.lfilter(*signal.butter(2, 3000 / (SR / 2)), rng.standard_normal(len(gt))) * np.exp(-gt / 0.08)
add(gong * 0.35 + thump * 0.6 + burst * 0.25, turn, 1.0)

# 5) мотив после поворота (мажорная пентатоника, тепло)
for i, tm in enumerate(T["motif"]):
    add(pluck(hz(["G4", "B4", "D5", "E5"][i]), 1.6, 0.9), real(tm), 0.3, pan=0.2 - 0.1 * i)

# 6) тики: каждая почка падает в горку
for i, tl in enumerate(T["budLand"]):
    n = int(0.05 * SR); tt = np.arange(n) / SR
    f = 2600 + 900 * rng.random()
    tick = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.012) + 0.3 * rng.standard_normal(n) * np.exp(-tt / 0.004)
    add(tick, real(tl), 0.16, pan=rng.uniform(-0.6, 0.6))

# 7) три колокола: 金 骏 眉
for i, tg in enumerate(T["glyphs"]):
    add(bell(hz(["G4", "B4", "D5"][i]), 2.2), real(tg), 0.22, pan=[-0.4, 0, 0.4][i])

# 8) печать: мягкий глухой удар; 9) финальный аккорд
st = np.arange(int(0.4 * SR)) / SR
add(np.sin(2 * np.pi * 110 * st) * np.exp(-st / 0.09) + 0.2 * rng.standard_normal(len(st)) * np.exp(-st / 0.02), real(T["seal"]), 0.5)
for j, nt in enumerate(["G3", "D4", "G4", "B4"]):
    add(bell(hz(nt), 3.6) * 0.7 + pluck(hz(nt), 3.6, 0.8) * 0.5, real(T["finalChord"]) + 0.06 * j, 0.15)

# стерео-реверб: несколько затухающих отражений
for d, g in [(0.031, 0.25), (0.047, 0.2), (0.071, 0.15), (0.113, 0.1)]:
    s = int(d * SR)
    L[s:] += Rch[:-s] * g; Rch[s:] += L[:-s] * g * 0.9

fade = np.clip((T["duration"] - t) / 0.8, 0, 1)
mix = np.stack([L * fade, Rch * fade], 1)
mix /= max(1e-9, np.abs(mix).max()) / 0.8
out = HERE / "out"; out.mkdir(exist_ok=True)
wavfile.write(out / "audio_raw.wav", SR, (mix * 32767).astype(np.int16))
print("audio_raw.wav ok", mix.shape)
