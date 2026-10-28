"""«Все кошки — мопсы». Звук коллажа синтезом по таймлайну timing.json: у каждого элемента свой звук.
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
rng = np.random.default_rng(1001)
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
def s_trap():     # «ловушка»: падающий свисток-«уа-уа» (тромбон с сурдиной)
    n = ns(0.55); tt = np.arange(n) / SR; f = 330 * 2 ** (-tt / 0.55 * 0.5) * (1 + 0.02 * np.sin(2 * np.pi * 6 * tt))
    ph = 2 * np.pi * np.cumsum(f) / SR; x = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)
    return bp(250, 2500, x) * env(n, 0.02, 0.3) * (0.65 + 0.35 * np.sin(2 * np.pi * 4.5 * tt))
def meow(dur=0.7, f0=620):  # «мяу»: гармоники с формантой, скользящей «и→а→у»
    n = ns(dur); tt = np.arange(n) / SR; u = tt / dur
    f = f0 * (1 + 0.35 * np.sin(np.pi * u ** 0.8)) ; ph = 2 * np.pi * np.cumsum(f) / SR
    src = sum(np.sin(k * ph) / k for k in range(1, 12))
    out = np.zeros(n); blk = 960
    for j in range(0, n, blk):
        uu = j / n; fc = 2400 - 1600 * uu if uu > 0.3 else 1500 + 3000 * uu
        out[j:j + blk] = bp(fc * 0.6, min(SR / 2 - 100, fc * 1.5), src[j:j + blk])
    return out * np.sin(np.pi * u) ** 0.7
def snort():      # фырканье мопса: низкий шумовой «хрюк»
    n = ns(0.35); x = bp(120, 900, noise(n)) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 28 * np.arange(n) / SR)))
    return x * env(n, 0.01, 0.12)
S = {
    "letter": s_letter, "key": s_key, "return": s_return, "trap": s_trap,
    "slide": lambda: bp(1200, 6000, noise(ns(0.3))) * np.sin(np.linspace(0, np.pi, ns(0.3))) ** 2 * 0.6,
    "drop": lambda: thud(80, 0.07, 0.4) + bp(800, 4000, noise(ns(0.4))) * env(ns(0.4), 0.01, 0.06) * 0.35,
    "tape": lambda: bp(1500, 7000, noise(ns(0.28))) * np.abs(np.sin(np.linspace(0, 40, ns(0.28)))) * np.linspace(1, 0.2, ns(0.28)),
    "slap": lambda: thud(140, 0.03, 0.15) * 0.8 + bp(2000, 8000, noise(ns(0.15))) * env(ns(0.15), 0.001, 0.012) * 0.8,
    "stamp": lambda: thud(70, 0.1, 0.5) * 1.2 + bp(300, 2000, noise(ns(0.5))) * env(ns(0.5), 0.001, 0.03) * 0.5,
}
GAIN = {"letter": 0.32, "key": 0.13, "return": 0.22, "slide": 0.25, "drop": 0.5, "tape": 0.3, "slap": 0.4, "stamp": 0.6, "trap": 0.32}
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
def band(a, b, fade=0.6): return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

# герои: «мяу» на кошке, фырканье на мопсе
sc = {s["id"]: s for s in T["scenes"]}; O = T["L"]["obj"]
add(meow(0.6, 640), 0.15, 0.16, pan=-0.3); add(snort(), 0.8, 0.3, pan=0.3)
for sid, kind in [("paws", "both"), ("poll", "pug"), ("prof", "pug"), ("dict", "cat"), ("face", "cat"), ("qed", "both")]:
    t0 = sc[sid]["local0"] + O + 0.3
    if kind in ("cat", "both"): add(meow(0.55, rng.uniform(560, 700)), t0, 0.12, pan=-0.3)
    if kind in ("pug", "both"): add(snort(), t0 + (0.45 if kind == "both" else 0), 0.25, pan=0.3)
q = sc["qed"]; add(meow(0.9, 700), q["local0"] + T["L"]["ins2"] + 0.1, 0.16, pan=-0.3)  # «я не мопс!»

# ---------- музыка: «учёная» шутка — фагот-пиццикато в до мажоре, по такту 0,5 с ----------
bass = ["C3", "G2", "A2", "E2", "F2", "C3", "G2", "G2"]
mel = ["E4", "G4", "C5", "G4", "A4", "F4", "D4", "G4", "E4", "C5", "B4", "G4", "A4", "C5", "D5", "B4"]
end = T["duration"] - 3.2
for i, tp in enumerate(np.arange(0.9, end, 0.5)):
    add(pluck(hz(bass[(i // 2) % len(bass)]), 0.5, 0.2), tp, 0.22 if i % 2 == 0 else 0.12, pan=-0.15)
    if i % 2 == 1: add(pluck(hz(mel[(i // 2) % len(mel)]), 0.9, 0.85), tp + 0.02, 0.11, pan=0.25)
for s0 in T["B"]: add(bell(hz("G5"), 1.2), s0 + 0.2, 0.05, pan=0.2)
# «тадам» на каждом «ДОКАЗАНО»
for s_ in T["scenes"]:
    tt0 = s_["local0"] + s_["sealAt"] + 0.05
    for j, nt in enumerate(["C5", "E5", "G5"]): add(pluck(hz(nt), 0.8, 0.9), tt0 + 0.05 * j, 0.1)
# финал: торжественный аккорд на «ДОКАЗАНО» последнего шага
fc = q["local0"] + q["sealAt"] + 0.1
for j, nt in enumerate(["C3", "G3", "C4", "E4", "G4", "C5"]): add(bell(hz(nt), 4) * 0.6 + pluck(hz(nt), 4, 0.8) * 0.5, fc + 0.06 * j, 0.14)
drone = (np.sin(2 * np.pi * 65.4 * t) + 0.4 * np.sin(2 * np.pi * 98 * t)) * band(0, T["duration"] + 2, 2)
L += drone * 0.02; R += drone * 0.02

for d_, g_ in [(0.031, 0.22), (0.047, 0.18), (0.071, 0.13), (0.113, 0.09)]:
    s_ = ns(d_); L[s_:] += R[:-s_] * g_; R[s_:] += L[:-s_] * g_ * 0.9
fade = np.clip((T["duration"] - t) / 1.0, 0, 1) * np.clip(t / 0.03, 0, 1)
mix = np.stack([L * fade, R * fade], 1); mix /= max(1e-9, np.abs(mix).max()) / 0.8
(HERE / "out").mkdir(exist_ok=True)
wavfile.write(HERE / "out" / "audio_raw.wav", SR, (mix * 32767).astype(np.int16))
print("audio_raw.wav ok", mix.shape, "events:", len(T["events"]))
