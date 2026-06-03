#!/usr/bin/env python3
"""重新生成TTS，用正确加速参数 +15%"""
import os, subprocess, json, tempfile, re

EP_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第2期_昇腾部署Qwen3-VL-8B概念讲解")
INPUT = os.path.join(EP_DIR, "02_口播稿/配音稿_分段.txt")
AUDIO_DIR = os.path.join(EP_DIR, "03_音频")
os.makedirs(AUDIO_DIR, exist_ok=True)

with open(INPUT) as f:
    content = f.read()

segments = []
for m in re.finditer(r"---\s*P(\d+)\s+(.+?)---\s*\n(.*?)(?=\n---\s*P|\Z)", content, re.DOTALL):
    segments.append({"page": int(m.group(1)), "title": m.group(2).strip(), "text": m.group(3).strip()})

print(f"📄 {len(segments)} 段, 使用 --rate=+15%")
total_duration = 0.0
results = []

for seg in segments:
    audio_file = os.path.join(AUDIO_DIR, f"page_{seg['page']:02d}_accel.mp3")
    chars = len(seg["text"].replace("\n","").replace(" ",""))
    print(f"  P{seg['page']:>2d} {chars:>4d}字...  ", end="", flush=True)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write(seg["text"])
        tf_path = tf.name

    try:
        r = subprocess.run(
            ["python3", "-m", "edge_tts", "--voice", "zh-CN-XiaoxiaoNeural",
             "-f", tf_path, "--write-media", audio_file, "--rate=+15%"],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"❌ {r.stderr[:80]}")
            continue
    finally:
        os.unlink(tf_path)

    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio_file],
        capture_output=True, text=True)
    dur = float(r.stdout.strip())
    total_duration += dur
    results.append({"page": seg["page"], "title": seg["title"], "duration": round(dur, 2), "chars": chars})
    print(f"✅ {dur:.2f}s")

print(f"\n📊 总时长: {total_duration:.1f}s ({total_duration/60:.1f}min)")

# 写timeline.json
slides = []
s = 0.0
for r in results:
    slides.append({"page": r["page"], "start": round(s, 2), "end": round(s + r["duration"], 2), "duration": r["duration"], "title": r["title"]})
    s += r["duration"]

tl_path = os.path.join(EP_DIR, "03_音频/timeline.json")
with open(tl_path, "w") as f:
    json.dump({"total_duration": round(total_duration, 2), "slides": slides}, f, ensure_ascii=False, indent=2)
print(f"💾 {tl_path}")

# 合并完整配音
concat_list = os.path.join(AUDIO_DIR, "concat.txt")
with open(concat_list, "w") as f:
    for r in results:
        fp = os.path.join(AUDIO_DIR, f"page_{r['page']:02d}_accel.mp3")
        f.write(f"file '{fp}'\n")

merged = os.path.join(AUDIO_DIR, "配音_加速.mp3")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-ac", "1", "-ar", "24000",
                "-b:a", "192k", merged], capture_output=True, text=True)

# 消音（去头尾空白）
trimmed = os.path.join(AUDIO_DIR, "配音_加速_trimmed.mp3")
subprocess.run(["ffmpeg", "-y", "-i", merged,
                "-af", "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB:"
                       "stop_periods=1:stop_duration=0:stop_threshold=-50dB",
                "-ac", "1", "-ar", "24000", trimmed], capture_output=True, text=True)

r2 = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", trimmed], capture_output=True, text=True)
print(f"🔊 配音_加速.mp3: 合并完成 ✅")
print(f"🔊 消音后: {float(r2.stdout.strip()):.1f}s ({float(r2.stdout.strip())/60:.1f}min)")
print(f"💾 timeline.json 已更新")
