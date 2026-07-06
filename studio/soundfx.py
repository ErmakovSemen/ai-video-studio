"""Synthesized sound-design layer — no downloads, no licensing.

Generates a soft singing-bowl 'ding' for the hook and gentle noise whooshes for scene
cuts, then mixes them under the existing audio. Perceived-quality lift for near zero cost.
"""
import os, wave, subprocess
import numpy as np


def _write_wav(path, samples, sr=44100):
    x = np.clip(samples, -1.0, 1.0)
    x16 = (x * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(x16.tobytes())


def _bell(sr=44100, dur=2.8, f0=320.0, gain=0.42):
    """Soft inharmonic singing-bowl tone with a long gentle decay."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    partials = [(1.0, 1.0), (2.01, 0.5), (2.71, 0.28), (3.83, 0.16), (5.1, 0.09)]
    x = np.zeros_like(t)
    for ratio, amp in partials:
        x += amp * np.sin(2 * np.pi * f0 * ratio * t)
    x /= sum(a for _, a in partials)
    env = np.exp(-t / (dur * 0.33))
    attack = np.clip(t / 0.008, 0, 1)
    return gain * x * env * attack


def _whoosh(sr=44100, dur=0.42, gain=0.16):
    """Short airy noise swell for scene transitions (high-passed, bell envelope)."""
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.randn(n)
    k = max(1, int(sr * 0.0022))
    lp = np.convolve(noise, np.ones(k) / k, mode="same")
    hp = noise - lp                                   # crude high-pass
    env = np.exp(-((t - dur / 2) ** 2) / (2 * (dur / 5) ** 2))
    return gain * hp * env


def add_sfx(video_in, video_out, cut_times, sr=44100, bell=True, whoosh=True):
    """Mix a bell at the hook + whooshes at each scene cut, under the existing audio."""
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", video_in], capture_output=True, text=True).stdout.strip())
    bed = np.zeros(int(sr * dur) + sr)

    def place(sig, at):
        i = int(sr * max(0.0, at)); j = min(len(bed), i + len(sig)); bed[i:j] += sig[:j - i]

    if bell:
        place(_bell(sr), 0.12)                         # hook cue just after the first frame
    if whoosh:
        for ct in cut_times[1:]:                       # whoosh at each scene change (skip start)
            place(_whoosh(sr), ct - 0.06)

    sfx = video_out + ".sfx.wav"
    _write_wav(sfx, bed[:int(sr * dur)], sr)
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_in, "-i", sfx, "-filter_complex",
         "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
         "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", video_out],
        capture_output=True)
    os.remove(sfx)
    return video_out
