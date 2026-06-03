#!/usr/bin/env python3
"""
tts_to_durations.py — 口播稿 → TTS 生成 → 分段时长测量

用法:
  python3 scripts/tts_to_durations.py --input 配音稿_分段.txt --generate
  python3 scripts/tts_to_durations.py --input 配音稿_分段.txt --parse-only
  python3 scripts/tts_to_durations.py --input 配音稿.txt --audio-dir audio/ --out-json timeline.json
"""

import argparse, json, os, re, subprocess, sys, tempfile

SEGMENT_RE = re.compile(
    r"---\s*P(\d+)\s+(.*?)\s*\((\d+(?:\.\d+)?)(?:s|秒|秒数)\)\s*---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL
)


def parse_segmented(path):
    with open(path) as f:
        content = f.read()
    return [{"page": int(m.group(1)), "title": m.group(2).strip(),
             "text": m.group(4).strip()}
            for m in SEGMENT_RE.finditer(content)]


def parse_simple(path):
    with open(path) as f:
        content = f.read()
    # P{n} markers or double-newline split
    parts = re.split(r"(?:^|\n)(?:---\s*P(\d+)|##\s*P(\d+))", content, flags=re.MULTILINE)
    segments = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if p is None or (isinstance(p, str) and p.strip() == ""):
            i += 1; continue
        if re.match(r"^\d+$", str(p).strip()):
            page = int(p.strip())
            i += 1
            text = parts[i].strip() if i < len(parts) else ""
            segments.append({"page": page, "title": f"P{page}", "text": text})
        i += 1
    if not segments:
        paras = re.split(r"\n\s*\n", content.strip())
        for idx, para in enumerate(paras):
            if para.strip():
                segments.append({"page": idx+1, "title": f"P{idx+1}", "text": para.strip()})
    return segments


def generate_tts(text, output_path, voice):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        tf.write(text)
        tf_path = tf.name
    try:
        r = subprocess.run(["python3","-m","edge_tts","--voice",voice,
                            "-f",tf_path,"--write-media",output_path],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"  ❌ edge-tts 失败: {r.stderr[:200]}", file=sys.stderr)
            return False
        return True
    finally:
        try:
            os.unlink(tf_path)
        except OSError:
            pass


def get_duration(audio_path):
    r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                        "-of","csv=p=0", audio_path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def remove_silence(audio_path, output_path):
    r = subprocess.run(
        ["ffmpeg","-y","-i",audio_path,
         "-af","silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB:"
                "stop_periods=1:stop_duration=0:stop_threshold=-50dB",
         output_path], capture_output=True, text=True)
    return r.returncode == 0


def measure(text, voice, speed, audio_file, do_generate):
    chars = len(text.replace("\n","").replace(" ",""))
    if do_generate or not os.path.exists(audio_file):
        print(f"  📢 TTS ({chars} 字)...", end=" ", flush=True)
        if not generate_tts(text, audio_file, voice):
            return None
        print("✓")

    raw = get_duration(audio_file)
    trimmed_file = audio_file.replace(".mp3","_trimmed.mp3")
    if remove_silence(audio_file, trimmed_file):
        trimmed = get_duration(trimmed_file)
        effective = trimmed if trimmed > 1.0 else raw
    else:
        effective = raw
    accel = effective / speed
    return {"raw": round(raw,2), "trimmed": round(effective,2),
            "accelerated": round(accel,2), "target": round(max(accel, 4.0), 1),
            "chars": chars}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--audio-dir", default="audio")
    p.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    p.add_argument("--speed", type=float, default=1.15)
    p.add_argument("--generate", action="store_true")
    p.add_argument("--parse-only", action="store_true")
    p.add_argument("--out-json")
    p.add_argument("--simple-format", action="store_true")
    args = p.parse_args()

    if args.parse_only:
        segs = parse_simple(args.input) if args.simple_format else parse_segmented(args.input)
        if not segs:
            segs = parse_simple(args.input)
        for s in segs:
            chars = len(s["text"].replace("\n","").replace(" ",""))
            print(f"P{s['page']:>2d}  {chars:>4d}字  {s.get('title','')}")
        return

    segs = parse_segmented(args.input) or parse_simple(args.input)
    if not segs:
        print("❌ 无法解析", file=sys.stderr)
        sys.exit(1)

    print(f"📄 {len(segs)} 段")
    os.makedirs(args.audio_dir, exist_ok=True)

    total_raw = 0; total_tgt = 0; results = []
    for seg in segs:
        af = os.path.join(args.audio_dir, f"page_{seg['page']:02d}.mp3")
        m = measure(seg["text"], args.voice, args.speed, af, args.generate)
        if m is None:
            print(f"  ❌ P{seg['page']} 失败")
            continue
        results.append({**seg, **m})
        print(f"  P{seg['page']:>2d} {m['raw']:>6.2f}s → 去静音 {m['trimmed']:>6.2f}s → {args.speed}x {m['accelerated']:>6.2f}s → 目标 {m['target']:>5.1f}s  ({m['chars']}字)")
        total_raw += m["raw"]
        total_tgt += m["target"]

    print(f"\n📊 {len(results)} 页  原始 {total_raw:.1f}s  加速 {total_tgt:.1f}s")
    start = 0.0
    print(f"\n📋 data-start 片段：")
    for r in results:
        dur = r["target"]
        print(f'  <div data-composition-id="s{r["page"]}" data-composition-src="compositions/scene_{r["page"]}.html" data-start="{start:.2f}" data-duration="{dur:.2f}" data-width="1920" data-height="1080"></div>')
        start += dur

    if args.out_json:
        slides = []
        s = 0.0
        for r in results:
            dur = r["target"]
            slides.append({"page": r["page"], "start": round(s,2), "end": round(s+dur,2), "duration": dur, "title": r.get("title","")})
            s += dur
        with open(args.out_json, "w") as f:
            json.dump({"total_duration": round(total_tgt,2), "slides": slides}, f, ensure_ascii=False, indent=2)
        print(f"\n💾 {args.out_json}")


if __name__ == "__main__":
    main()
