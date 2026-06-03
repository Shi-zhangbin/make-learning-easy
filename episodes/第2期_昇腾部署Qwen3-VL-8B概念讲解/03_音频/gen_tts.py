#!/usr/bin/env python3
"""手动生成TTS分段配音 + 测量时长"""
import os, subprocess, json, tempfile, re

EP_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第2期_昇腾部署Qwen3-VL-8B概念讲解")
INPUT = os.path.join(EP_DIR, "02_口播稿/配音稿_分段.txt")
AUDIO_DIR = os.path.join(EP_DIR, "03_音频")
os.makedirs(AUDIO_DIR, exist_ok=True)

# 读取并手动分段
with open(INPUT) as f:
    content = f.read()

segments = []
for m in re.finditer(r"---\s*P(\d+)\s+(.+?)---\s*\n(.*?)(?=\n---\s*P|\Z)", content, re.DOTALL):
    page = int(m.group(1))
    title = m.group(2).strip()
    text = m.group(3).strip()
    segments.append({"page": page, "title": title, "text": text})

print(f"📄 {len(segments)} 段")
total_duration = 0.0
results = []

for seg in segments:
    audio_file = os.path.join(AUDIO_DIR, f"page_{seg['page']:02d}.mp3")
    chars = len(seg["text"].replace("\n","").replace(" ",""))
    
    print(f"  P{seg['page']:>2d} {chars:>4d}字  {seg['title'][:20]}...  ", end="", flush=True)
    
    # 生成TTS
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write(seg["text"])
        tf_path = tf.name
    
    try:
        r = subprocess.run(
            ["python3", "-m", "edge_tts", "--voice", "zh-CN-XiaoxiaoNeural",
             "-f", tf_path, "--write-media", audio_file,
             "--rate=-15%"],
            capture_output=True, text=True, timeout=300
        )
        if r.returncode != 0:
            print(f"❌ 失败: {r.stderr[:100]}")
            continue
    finally:
        os.unlink(tf_path)
    
    # 测量时长
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

# 输出data-start片段
print(f"\n📋 data-start 片段：")
start = 0.0
for r in results:
    dur = r["duration"]
    print(f'  <div data-composition-id="s{r["page"]}" data-composition-src="compositions/scene_{r["page"]}.html" data-start="{start:.2f}" data-duration="{dur:.2f}" data-width="1920" data-height="1080"></div>')
    start += dur

# 输出timeline.json
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
print(f"\n💾 {tl_path}")
