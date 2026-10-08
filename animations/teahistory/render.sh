#!/usr/bin/env bash
# Полная сборка: ./render.sh [draft|standard|high]
set -euo pipefail
cd "$(dirname "$0")"
Q=${1:-high}
mkdir -p out
python3 build_timing.py
python3 audio.py
ffmpeg -loglevel error -y -i out/audio_raw.wav -af loudnorm=I=-15:TP=-1.5:LRA=11 -ar 48000 out/audio.wav
npx --yes hyperframes@0.8.114 render -c index.html -f 24 -q "$Q" -o out/teahistory_silent.mp4 2>&1 | grep -E "rendered in|rror" || true
ffmpeg -loglevel error -y -i out/teahistory_silent.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart out/teahistory.mp4
rm -f out/teahistory_silent.mp4
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration -of csv=p=0 out/teahistory.mp4
ffmpeg -nostats -i out/audio.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
