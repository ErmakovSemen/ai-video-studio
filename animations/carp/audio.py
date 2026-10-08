"""Звук дневника синтезом по таймлайну timing.json: у каждого элемента свой звук.
скотч — треск отрыва, наклейка — шлепок, полароид — глухой стук, стикер — мягкий хлопок,
печать — удар, маркер — скрип, рука пишет — шорох карандаша, листание — шелест. Плюс вода и музыка."""
import json, pathlib
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = pathlib.Path(__file__).parent
T = json.loads((HERE / "timing.json").read_text())
SR = 48000
N = int(T["duration"] * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(1949)
t = np.arange(N) / SR

def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2); R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)
bp = lambda lo, hi, x: signal.lfilter(*signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band"), x)
env = lambda n, a, dcy: np.minimum(1, np.arange(n) / SR / a) * np.exp(-np.arange(n) / SR / dcy)
def hz(note):
    names = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}
    return 440 * 2 ** ((names[note[0]] + 12 * (int(note[-1]) - 4)) / 12)
def pluck(f, dur=1.6, bright=0.5):
    n = int(dur * SR); p = int(SR / f); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.994 + 0.005 * bright)
    return out * env(n, 0.002, dur * 0.6)
def bell(f, dur=2.5):
    tt = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt / (dur * d)) for m, a, d in [(1, 1, 1), (2.76, 0.4, 0.5), (5.4, 0.2, 0.25)]) * np.minimum(1, tt / 0.003)
def noise(n): return rng.standard_normal(n)
def thud(f=90, dcy=0.08, n=0.3): tt = np.arange(int(n * SR)) / SR; return np.sin(2 * np.pi * (f + 50 * np.exp(-tt / 0.02)) * tt) * np.exp(-tt / dcy)

S = {}
S["tape"] = lambda: bp(1500, 7000, noise(int(0.28 * SR))) * np.abs(np.sin(np.linspace(0, 40, int(0.28 * SR)))) * np.linspace(1, 0.2, int(0.28 * SR))
S["sticker"] = lambda: thud(140, 0.03, 0.15) * 0.8 + bp(2000, 8000, noise(int(0.15 * SR))) * env(int(0.15 * SR), 0.001, 0.012) * 0.8
S["drop"] = lambda: thud(80, 0.07, 0.4) + bp(800, 4000, noise(int(0.4 * SR))) * env(int(0.4 * SR), 0.01, 0.06) * 0.35
S["sticky"] = lambda: thud(120, 0.04, 0.2) * 0.6 + bp(1000, 5000, noise(int(0.2 * SR))) * env(int(0.2 * SR), 0.002, 0.03) * 0.4
S["stamp"] = lambda: thud(70, 0.1, 0.5) * 1.2 + bp(300, 2000, noise(int(0.5 * SR))) * env(int(0.5 * SR), 0.001, 0.03) * 0.5
S["mark"] = lambda: bp(2500, 6000, noise(int(0.4 * SR))) * (0.5 + 0.5 * np.sin(np.linspace(0, 60, int(0.4 * SR)))) * np.sin(np.linspace(0, np.pi, int(0.4 * SR))) * 0.6
GAIN = {"tape": 0.35, "sticker": 0.45, "drop": 0.5, "sticky": 0.35, "stamp": 0.6, "mark": 0.25}

scratch = bp(1800, 7000, noise(N)); gate = np.zeros(N)
for e in T["events"]:
    k = e["kind"]
    if k in S: add(S[k](), e["t"], GAIN[k], pan=rng.uniform(-0.4, 0.4))
    if k in ("write", "drop"):   # карандаш пишет / рисует фото
        a = e["t"] + (0.3 if k == "drop" else 0); gate[int(a * SR):int((a + 1.4) * SR)] = 1
    if k == "burst":             # поворот: вспышка наклеек-звёзд + колокольчики
        for j, nt in enumerate(["G5", "B5", "D6", "G6"]): add(bell(hz(nt), 1.6), e["t"] + 0.12 * j, 0.12, pan=-0.3 + 0.2 * j)
gate = signal.lfilter([1 / 2400], [1, -1 + 1 / 2400], gate)
k12 = np.floor(t * T["drawRate"]).astype(int)
L += scratch * gate * rng.uniform(0.35, 1, k12.max() + 2)[k12] * 0.04; R += scratch * gate * 0.035

# листание страниц
for b in T["B"]:
    n = int(0.6 * SR); src = noise(n); out = np.zeros(n)
    for j in range(0, n, 1200):
        fc = 1500 + 3000 * np.sin(np.pi * j / n); out[j:j + 1200] = bp(fc * 0.7, min(SR / 2 - 100, fc * 1.4), src[j:j + 1200])
    add(out * np.sin(np.pi * np.arange(n) / n), b + 0.05, 0.4, pan=0.3)
    add(thud(100, 0.05, 0.2), b + 0.85, 0.3)

# вода: река и водопад (страницы 2–4), всплеск при прыжке
w0, w1 = T["start"][1], T["start"][4] + 0.5
water = bp(200, 1600, noise(N)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t))
wg = np.clip((t - w0) / 0.8, 0, 1) * np.clip((w1 - t) / 0.8, 0, 1) * np.where(t > T["start"][2], 1.6, 1.0)
L += water * wg * 0.05; R += water * wg * 0.05
sp = int(0.6 * SR); add(bp(500, 5000, noise(sp)) * env(sp, 0.005, 0.15), T["turn"] - 0.5, 0.5)

# музыка: пентатоника, после прыжка теплее; финальный аккорд
for i, tp in enumerate(np.arange(0.4, T["turn"], 1.45)):
    add(pluck(hz(["A3", "C4", "E4", "D4", "G3", "E4", "A3", "D4"][i % 8]), 1.8, 0.3), tp, 0.22, pan=-0.3 + 0.08 * (i % 7))
for i, tp in enumerate(np.arange(T["turn"] + 0.6, T["duration"] - 4, 1.2)):
    add(pluck(hz(["G4", "B4", "D5", "E5", "D5", "B4"][i % 6]), 1.6, 0.9), tp, 0.22, pan=0.25 - 0.08 * (i % 6))
fc = T["start"][5] + 4.5
for j, nt in enumerate(["G3", "D4", "G4", "B4"]): add(bell(hz(nt), 4) * 0.7 + pluck(hz(nt), 4, 0.8) * 0.5, fc + 0.08 * j, 0.15)
drone = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)) * np.clip(t / 2, 0, 1) * np.clip((T["duration"] - t) / 2, 0, 1)
L += drone * 0.035; R += drone * 0.035

for d_, g_ in [(0.031, 0.25), (0.047, 0.2), (0.071, 0.15), (0.113, 0.1)]:
    s_ = int(d_ * SR); L[s_:] += R[:-s_] * g_; R[s_:] += L[:-s_] * g_ * 0.9
fade = np.clip((T["duration"] - t) / 1.0, 0, 1)
mix = np.stack([L * fade, R * fade], 1); mix /= max(1e-9, np.abs(mix).max()) / 0.8
(HERE / "out").mkdir(exist_ok=True)
wavfile.write(HERE / "out" / "audio_raw.wav", SR, (mix * 32767).astype(np.int16))
print("audio_raw.wav ok", mix.shape)
