#!/usr/bin/env bash
# Полная сборка: ./render.sh [draft|standard|high]
set -euo pipefail
cd "$(dirname "$0")"
Q=${1:-high}
mkdir -p out
python3 build_timing.py
python3 audio.py
# громкость в два прохода: замер, затем точная нормализация к −15 LUFS (один проход недотягивал до −16)
LN="I=-15:TP=-1.5:LRA=11"
M=$(ffmpeg -hide_banner -i out/audio_raw.wav -af "loudnorm=$LN:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
v() { echo "$M" | python3 -c "import sys, json; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -loglevel error -y -i out/audio_raw.wav -af "loudnorm=$LN:measured_I=$(v input_i):measured_TP=$(v input_tp):measured_LRA=$(v input_lra):measured_thresh=$(v input_thresh):offset=$(v target_offset)" -ar 48000 out/audio.wav
npx --yes hyperframes@0.8.114 render -c index.html -f 24 -q "$Q" -o out/catpug_silent.mp4 2>&1 | grep -E "rendered in|rror" || true
ffmpeg -loglevel error -y -i out/catpug_silent.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart out/catpug.mp4
rm -f out/catpug_silent.mp4
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration -of csv=p=0 out/catpug.mp4
ffmpeg -nostats -i out/audio.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
