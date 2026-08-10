"""Generate Yandex SpeechKit samples (same line) across premium RU voices -> WAV."""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from studio import tts_yandex

OUT = os.path.join(ROOT, "outputs", "voice_samples")
os.makedirs(OUT, exist_ok=True)
LINE = ("Перед боем самураи пили не саке. А чай. "
        "Одна чаша — и ум становится ясным и собранным.")

# premium female + male voices; alena/jane warm female, filipp/ermil/zahar male
VOICES = [("alena", "neutral"), ("jane", "good"), ("omazh", "neutral"),
          ("filipp", "neutral"), ("ermil", "good"), ("zahar", "neutral")]

for v, emo in VOICES:
    out = os.path.join(OUT, f"yandex_{v}.wav")
    print(f"yandex {v} ({emo})...", flush=True)
    try:
        tts_yandex.synth(LINE, out, voice=v, emotion=emo)
        print(f"  ok {os.path.getsize(out)//1024}kb", flush=True)
    except Exception as e:
        print(f"  FAIL {e}", flush=True)
print("DONE", flush=True)
