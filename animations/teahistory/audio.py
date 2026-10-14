"""Звук коллажа синтезом по таймлайну timing.json: у каждого элемента свой звук.
буква заголовка — бумажный шлепок, гравюра — глухой стук, скотч — треск, марка/билет — хлопок,
машинка — щелчки клавиш и возврат каретки, печать — удар, смена листа — шорох бумаги.
Фон по главам: огонь и бульканье (легенда), кипение (самовар), налив (сегодня). Музыка: Китай → Россия → сегодня."""
import json, pathlib
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = pathlib.Path(__file__).parent
T = json.loads((HERE / "timing.json").read_text())
SR = 48000
N = int(T["duration"] * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(2737)
t = np.arange(N) / SR
ST = [s["start"] for s in T["scenes"]]

def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2); R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)
bp = lambda lo, hi, x: signal.lfilter(*signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band"), x)
env = lambda n, a, dcy: np.minimum(1, np.arange(n) / SR / a) * np.exp(-np.arange(n) / SR / dcy)
ns = lambda d: int(d * SR)
def hz(note):
    names = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}
    return 440 * 2 ** ((names[note[0]] + ('#' in note) + 12 * (int(note[-1]) - 4)) / 12)
def pluck(f, dur=1.6, bright=0.5):
    n = ns(dur); p = int(SR / f); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.994 + 0.005 * bright)
    return out * env(n, 0.002, dur * 0.6)
def bell(f, dur=2.5):
    tt = np.arange(ns(dur)) / SR
    return sum(a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt / (dur * d)) for m, a, d in [(1, 1, 1), (2.76, 0.4, 0.5), (5.4, 0.2, 0.25)]) * np.minimum(1, tt / 0.003)
def noise(n): return rng.standard_normal(n)
def thud(f=90, dcy=0.08, n=0.3): tt = np.arange(ns(n)) / SR; return np.sin(2 * np.pi * (f + 50 * np.exp(-tt / 0.02)) * tt) * np.exp(-tt / dcy)

# ---------- звуки элементов ----------
def s_letter():   # бумажная буква шлепается на лист
    n = ns(0.12); return thud(rng.uniform(150, 230), 0.02, 0.12) * 0.7 + bp(1500, 7000, noise(n)) * env(n, 0.001, 0.014)
def s_key():      # клавиша машинки: щелчок + корпус
    n = ns(0.06); return bp(2500, 9000, noise(n)) * env(n, 0.0003, 0.004) + thud(rng.uniform(170, 210), 0.012, 0.06) * 0.6
def s_return():   # возврат каретки: «вжик», удар и тихий звоночек
    n = ns(0.22); zip_ = bp(900, 4000, noise(n)) * np.abs(np.sin(np.linspace(0, 70, n))) * np.linspace(0.3, 1, n) * 0.5
    out = np.concatenate([zip_, thud(120, 0.03, 0.1), np.zeros(ns(0.3))]); ding = bell(2200, 0.5) * 0.15
    out[: len(ding)] += ding; return out
S = {
    "letter": s_letter, "key": s_key, "return": s_return,
    "slide": lambda: bp(1200, 6000, noise(ns(0.3))) * np.sin(np.linspace(0, np.pi, ns(0.3))) ** 2 * 0.6,
    "drop": lambda: thud(80, 0.07, 0.4) + bp(800, 4000, noise(ns(0.4))) * env(ns(0.4), 0.01, 0.06) * 0.35,
    "tape": lambda: bp(1500, 7000, noise(ns(0.28))) * np.abs(np.sin(np.linspace(0, 40, ns(0.28)))) * np.linspace(1, 0.2, ns(0.28)),
    "slap": lambda: thud(140, 0.03, 0.15) * 0.8 + bp(2000, 8000, noise(ns(0.15))) * env(ns(0.15), 0.001, 0.012) * 0.8,
    "stamp": lambda: thud(70, 0.1, 0.5) * 1.2 + bp(300, 2000, noise(ns(0.5))) * env(ns(0.5), 0.001, 0.03) * 0.5,
}
GAIN = {"letter": 0.32, "key": 0.13, "return": 0.22, "slide": 0.25, "drop": 0.5, "tape": 0.3, "slap": 0.4, "stamp": 0.6}
for e in T["events"]:
    k = e["kind"]
    if k in S: add(S[k](), e["t"], GAIN[k] * rng.uniform(0.8, 1.0), pan=rng.uniform(-0.35, 0.35))

# смена листа: шорох бумаги + лёгкое касание
for b in T["B"]:
    n = ns(0.6); src = noise(n); out = np.zeros(n)
    for j in range(0, n, 1200):
        fc = 1500 + 3000 * np.sin(np.pi * j / n); out[j:j + 1200] = bp(fc * 0.7, min(SR / 2 - 100, fc * 1.4), src[j:j + 1200])
    add(out * np.sin(np.pi * np.arange(n) / n), b, 0.45, pan=0.35)
    add(thud(100, 0.05, 0.2), b + 0.55, 0.25)

# ---------- фон глав ----------
def band(a, b, fade=0.6): return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)
# легенда: огонь (треск) и бульканье котла
crackle = np.zeros(N)
for tc in rng.uniform(0.4, ST[1], 70): i = int(tc * SR); m = ns(0.02); crackle[i:i + m] += bp(1500, 6000, noise(m)) * env(m, 0.0005, 0.004)[: len(crackle[i:i + m])] * rng.uniform(0.3, 1)
fire = bp(150, 900, noise(N)) * 0.4 + crackle
L += fire * band(0.3, ST[1] + 0.3) * 0.06; R += fire * band(0.3, ST[1] + 0.3) * 0.05
for tb in np.sort(rng.uniform(1.4, ST[1], 26)): add(np.sin(2 * np.pi * np.linspace(300, 700, ns(0.05)).cumsum() / SR) * env(ns(0.05), 0.003, 0.015), tb, 0.05, pan=rng.uniform(-0.3, 0.3))
# самовар: тихое кипение
boil = bp(400, 2500, noise(N)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t))
L += boil * band(ST[5] + 1.2, ST[6] + 0.3) * 0.035; R += boil * band(ST[5] + 1.2, ST[6] + 0.3) * 0.035
# сегодня: налив чая в чашку
pn = ns(1.6); pour = bp(500, 3000, noise(pn)) * (0.6 + 0.4 * np.sin(np.linspace(0, 90, pn)) ** 2) * np.sin(np.linspace(0, np.pi, pn)) ** 0.5
add(pour, T["scenes"][6]["local0"] + T["L"]["obj"] + 0.15, 0.18)

# ---------- музыка ----------
# главы 1–4: китайская пентатоника (ля), щипок «гуциня» + колокольчик в начале главы
cn = ["A3", "C4", "D4", "E4", "G4", "E4", "D4", "C4", "A3", "G3", "A3", "E4"]
for i, tp in enumerate(np.arange(0.5, ST[4] - 0.6, 1.3)):
    add(pluck(hz(cn[i % len(cn)]), 1.8, 0.35), tp, 0.2, pan=-0.3 + 0.06 * (i % 9))
for s0 in ST[:4]: add(bell(hz("E5"), 2.2), s0 + 0.25, 0.07, pan=0.2)
# главы 5–6: Россия — ре минор, щипки «балалайки» парами (тремоло)
ru = ["D4", "F4", "A4", "G4", "F4", "E4", "D4", "A3"]
for i, tp in enumerate(np.arange(ST[4] + 0.3, ST[6] - 0.5, 1.1)):
    f = hz(ru[i % len(ru)])
    for j in range(3): add(pluck(f, 0.9, 0.9), tp + j * 0.07, 0.13 * (1 - 0.25 * j), pan=0.2)
# глава 7: тёплый соль мажор и финальный аккорд на печати 茶
for i, tp in enumerate(np.arange(ST[6] + 0.4, ST[6] + 5.5, 1.0)):
    add(pluck(hz(["G4", "B4", "D5", "B4", "E5", "D5"][i % 6]), 1.6, 0.9), tp, 0.2, pan=0.25 - 0.08 * (i % 6))
fc = T["scenes"][6]["local0"] + T["scenes"][6]["sealAt"] + 0.1
for j, nt in enumerate(["G3", "D4", "G4", "B4", "D5"]): add(bell(hz(nt), 4) * 0.6 + pluck(hz(nt), 4, 0.8) * 0.5, fc + 0.07 * j, 0.14)
drone = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)) * band(0, ST[4], 2)
drone += (np.sin(2 * np.pi * 73.4 * t) + 0.5 * np.sin(2 * np.pi * 110 * t)) * band(ST[4], ST[6], 2)
drone += (np.sin(2 * np.pi * 98 * t) + 0.5 * np.sin(2 * np.pi * 146.8 * t)) * band(ST[6], T["duration"] + 2, 2)
L += drone * 0.03; R += drone * 0.03

for d_, g_ in [(0.031, 0.22), (0.047, 0.18), (0.071, 0.13), (0.113, 0.09)]:
    s_ = ns(d_); L[s_:] += R[:-s_] * g_; R[s_:] += L[:-s_] * g_ * 0.9
fade = np.clip((T["duration"] - t) / 1.0, 0, 1) * np.clip(t / 0.03, 0, 1)
mix = np.stack([L * fade, R * fade], 1); mix /= max(1e-9, np.abs(mix).max()) / 0.8
(HERE / "out").mkdir(exist_ok=True)
wavfile.write(HERE / "out" / "audio_raw.wav", SR, (mix * 32767).astype(np.int16))
print("audio_raw.wav ok", mix.shape, "events:", len(T["events"]))
