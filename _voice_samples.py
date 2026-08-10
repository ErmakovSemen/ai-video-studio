"""Generate comparison TTS samples: edge-tts vs Silero (RU), same line."""
import os, sys, subprocess, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "outputs", "voice_samples")
os.makedirs(OUT, exist_ok=True)

LINE = ("Перед боем самураи пили не саке. А чай. "
        "Одна чаша — и ум становится ясным и собранным.")

def to_mp3(wav, mp3):
    subprocess.run(["ffmpeg", "-y", "-i", wav, "-c:a", "libmp3lame", "-q:a", "3", mp3],
                   capture_output=True)
    if os.path.exists(wav):
        os.remove(wav)

# --- edge-tts (current) ---
def edge(voice, out_mp3):
    cli = os.path.join(os.path.dirname(sys.executable), "edge-tts")
    subprocess.run([cli, "--voice", voice, "--rate", "+8%", "--text", LINE,
                    "--write-media", out_mp3], capture_output=True)

print("edge-tts Svetlana...", flush=True)
edge("ru-RU-SvetlanaNeural", os.path.join(OUT, "edge_svetlana.mp3"))
print("edge-tts Dmitry...", flush=True)
edge("ru-RU-DmitryNeural", os.path.join(OUT, "edge_dmitry.mp3"))

# --- Silero v4_ru ---
import torch
print("loading Silero v4_ru (first run downloads ~60MB)...", flush=True)
model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models', model='silero_tts',
                          language='ru', speaker='v4_ru', trust_repo=True)
model.to('cpu')
for spk in ["baya", "kseniya", "xenia", "eugene", "aidar"]:
    print(f"silero {spk}...", flush=True)
    wav = model.save_wav(text=LINE, speaker=spk, sample_rate=48000,
                         audio_path=os.path.join(OUT, f"silero_{spk}.wav"))
    to_mp3(wav, os.path.join(OUT, f"silero_{spk}.mp3"))

print("DONE. files:", flush=True)
for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    print(" ", f, os.path.getsize(p)//1024, "kb", flush=True)
