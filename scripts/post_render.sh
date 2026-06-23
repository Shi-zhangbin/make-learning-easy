#!/bin/bash
# post_render.sh — 渲染完成后：加音频 + 烧字幕
EP_DIR="$HOME/Desktop/ascend-pipeline/episodes/第4_Transformer是什么"
RENDER_OUT="/tmp/v3_transformer_final.mp4"

echo "等待渲染完成..."
while [ ! -f "$RENDER_OUT" ] || [ "$(stat -f%z "$RENDER_OUT" 2>/dev/null)" -lt 1000 ]; do
  sleep 30
  SIZE="$(stat -f%z "$RENDER_OUT" 2>/dev/null || echo 0)"
  echo "  $(date '+%H:%M:%S') 渲染文件: $SIZE bytes"
done

echo "✅ 渲染完成!"
echo ""

# 1. 添加音频
AUDIO="$EP_DIR/audio/narration.mp3"
VIDEO_AUDIO="$EP_DIR/成品/with_audio.mp4"
mkdir -p "$EP_DIR/成品"

echo "🎵 添加音频..."
ffmpeg -y -i "$RENDER_OUT" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 192k \
  -map 0:v:0 -map 1:a:0 -shortest \
  "$VIDEO_AUDIO" 2>/dev/null && echo "  ✅ 音频合成完成" || echo "  ❌ 音频合成失败"

# 2. 烧录字幕
ASS="$EP_DIR/audio/narration.ass"
FINAL="$EP_DIR/成品/final.mp4"

if [ -f "$ASS" ]; then
  echo "📝 烧录字幕..."
  ffmpeg -y -i "$VIDEO_AUDIO" \
    -vf "subtitles=$ASS" \
    -c:a copy \
    "$FINAL" 2>/dev/null && echo "  ✅ 字幕烧录完成" || echo "  ❌ 字幕烧录失败"
else
  cp "$VIDEO_AUDIO" "$FINAL"
fi

# 3. 最终文件信息
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FINAL" 2>/dev/null)
SIZE=$(stat -f%z "$FINAL" 2>/dev/null)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎉 视频制作完成!"
echo "  📁 $FINAL"
echo "  ⏱  $DUR 秒"
echo "  📦 $((SIZE / 1048576)) MB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
