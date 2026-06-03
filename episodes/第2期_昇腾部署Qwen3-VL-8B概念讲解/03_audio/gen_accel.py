#!/usr/bin/env python3
"""重新生成TTS，用正确的加速参数 +15%"""
import os, subprocess, json, tempfile, re

EP_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第2期_昇腾部署Qwen3-VL-8B概念讲解")
INPUT = os.path.join(EP_DIR, "02_口播稿/配音稿_分段.txt")
AUDIO_DIR = os.path.join(EP_DIR, "03_音频")
os.makedirs(AUDIO_DIR, exist_ok=True)

with open(INPUT) as f:
    content = f.read()

segments = []
for m in re.finditer(r"---\s*P(\d+)\s+(.+?)---\s*\n(.*?)(?=\n---\s*P|\Z)", content, re.DOTALL):
    page = int(m.group(1))
    title = m.group(2).strip()
    text = m.group(3).strip()
    segments.append({"page": page, "title": title, "text": text})

print(f"📄 {len(segments)} 段")
print("使用 --rate=+15% (加速15%，服务端变速)")

total_duration = 0.0
results = []

for seg in segments:
    audio_file = os.path.join(AUDIO_DIR, f"page_{seg['page']:02d}_accel.mp3")
    chars = len(seg["text"].replace("\n","").replace(" ",""))
    
    print(f"  P{seg['page']:>2d} {chars:>4d}字  {seg['title'][:20]}...  ", end="", flush=True)
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write(seg["text"])
        tf_path = tf.name
    
    try:
        r = subprocess.run(
            ["python3", "-m", "edge_tts", "--voice", "zh-CN-XiaoxiaoNeural",
             "-f", tf_path, "--write-media", audio_file,
             "--rate=+15%"],  # ✅ 正确加速
            capture_output=True, text=True, timeout=300
        )
        if r.returncode != 0:
            print(f"❌ 失败: {r.stderr[:100]}")
            continue
    finally:
        os.unlink(tf_path)
    
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio_file],
        capture_output=True, text=True
    )
    duration = float(r.stdout.strip())
    total_duration += duration
    results.append({"page": seg["page"], "title": seg["title"], "duration": round(duration, 2), "chars": chars})
    print(f"✅ {duration:.2f}s")

print(f"\n📊 总时长: {total_duration:.1f}s ({total_duration/60:.1f}min)")

# 更新timeline.json
slides = []
s = 0.0
for r in results:
    dur = r["duration"]
    slides.append({"page": r["page"], "start": round(s,2), "end": round(s+dur,2), "duration": dur, "title": r["title"]})
    s += dur

timeline = {"total_duration": round(total_duration, 2), "slides": slides}
tl_path = os.path.join(EP_DIR, "03_音频/timeline.json")
with open(tl_path, "w") as f:
    json.dump(timeline, f, ensure_ascii=False, indent=2)
print(f"💾 {tl_path}")

# 也合并一个完整配音文件
print("\n🔊 合并完整配音...")
files = [os.path.join(AUDIO_DIR, f"page_{r['page']:02d}_accel.mp3") for r in results]
list_path = os.path.join(AUDIO_DIR, "concat_list.txt")
with open(list_path, "w") as f:
    for fp in files:
        f.write(f"file '{fp}'\n")

merged = os.path.join(AUDIO_DIR, "配音_加速.mp3")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_path, "-ac", "1", "-ar", "24000",
                "-b:a", "192k", merged],
               capture_output=True, text=True)
print(f"✅ 合并完成: {merged}")
