#!/usr/bin/env bash
# Полная сборка: [VOICE=aleksandr-hq RATE=120] ./render.sh [kraft|ink|all] [draft|standard|high]
# С VOICE дополнительно собирается версия с озвучкой (*_voice.mp4); видео рендерится один раз.
set -euo pipefail
cd "$(dirname "$0")"
THEMES=${1:-all}; Q=${2:-high}
[ "$THEMES" = all ] && THEMES="kraft ink"
mkdir -p out
python3 build_timing.py
rm -f out/voice.wav
[ -n "${VOICE:-}" ] && python3 voice.py
python3 audio.py
norm() { ffmpeg -loglevel error -y -i "$1" -af loudnorm=I=-15:TP=-1.5:LRA=11 -ar 48000 "$2"; }
norm out/audio_raw.wav out/audio.wav
[ -n "${VOICE:-}" ] && norm out/audio_voice_raw.wav out/audio_voice.wav
mux() { ffmpeg -loglevel error -y -i "$1" -i "$2" -map 0:v -map 1:a -c:v libx264 -crf 21 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart "$3"; echo "== $3"; ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration -of csv=p=0 "$3"; }
for th in $THEMES; do
  comp=index.html
  if [ "$th" != kraft ]; then comp="_$th.html"; sed "s/window.THEME = 'kraft'/window.THEME = '$th'/" index.html > "$comp"; fi
  npx --yes hyperframes@0.8.114 render -c "$comp" -f 24 -q "$Q" -o "out/${th}_silent.mp4" 2>&1 | grep -E "rendered in|rror" || true
  [ "$comp" != index.html ] && rm -f "$comp"
  mux "out/${th}_silent.mp4" out/audio.wav "out/jinjunmei_${th}.mp4"
  [ -n "${VOICE:-}" ] && mux "out/${th}_silent.mp4" out/audio_voice.wav "out/jinjunmei_${th}_voice.mp4"
  rm -f "out/${th}_silent.mp4"
done
for a in out/audio.wav out/audio_voice.wav; do [ -f "$a" ] && { echo "$a"; ffmpeg -nostats -i "$a" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2; }; done
