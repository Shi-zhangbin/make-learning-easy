#!/usr/bin/env bash
# 渲染完成后执行：bash 合成配音.sh
# 将渲染视频 + TTS配音合并

set -euo pipefail
cd "$(dirname "$0")"

VIDEO="05_视频成品/final.mp4"
AUDIO="03_audio/配音_加速_std.mp3"
OUTPUT="05_视频成品/第3期_Qwen3.5-9B推理调优_有声.mp4"

echo "🎬 合成有声视频..."
echo "   视频: $VIDEO"
echo "   音频: $AUDIO"
echo "   输出: $OUTPUT"

ffmpeg -i "$VIDEO" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 192k \
  -map 0:v:0 -map 1:a:0 -shortest \
  -y "$OUTPUT"

echo "✅ 合成完成: $OUTPUT"
echo ""
echo "📊 文件信息:"
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUTPUT"
