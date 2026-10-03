#!/usr/bin/env bash
# Полная сборка: ./render.sh [kraft|ink|all] [draft|standard|high]
set -euo pipefail
cd "$(dirname "$0")"
THEMES=${1:-all}; Q=${2:-high}
[ "$THEMES" = all ] && THEMES="kraft ink"
mkdir -p out
python3 build_timing.py
# звук: синтез + нормализация до -15 LUFS, пик -1 dBTP
python3 audio.py
ffmpeg -loglevel error -y -i out/audio_raw.wav -af loudnorm=I=-15:TP=-1.5:LRA=11 -ar 48000 out/audio.wav
for th in $THEMES; do
  comp=index.html
  if [ "$th" != kraft ]; then comp="_$th.html"; sed "s/window.THEME = 'kraft'/window.THEME = '$th'/" index.html > "$comp"; fi
  npx --yes hyperframes@0.8.114 render -c "$comp" -f 24 -q "$Q" -o "out/${th}_silent.mp4" 2>&1 | grep -E "rendered in|rror" || true
  [ "$comp" != index.html ] && rm -f "$comp"
  ffmpeg -loglevel error -y -i "out/${th}_silent.mp4" -i out/audio.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "out/jinjunmei_${th}.mp4"
  rm -f "out/${th}_silent.mp4"
  echo "== out/jinjunmei_${th}.mp4"
  ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration -of csv=p=0 "out/jinjunmei_${th}.mp4"
done
ffmpeg -nostats -i out/audio.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
