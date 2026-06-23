"""
v3/gates/post_render.py — 渲染后视频质量检查

在 T7 渲染完成后运行，检查：
1. 视频文件存在且大小正常
2. 视频时长 vs timeline 总时长偏差
3. 字幕末句结束时间 vs 视频时长偏差
4. 音频存在
"""
import json, subprocess, os, re
from pathlib import Path


def check_video(episode_dir: str) -> list[str]:
    """Run all post-render checks. Returns list of issues (empty = all passed)."""
    issues = []
    ep = Path(episode_dir)
    
    # Find final video
    final_candidates = list((ep / "成品").glob("*final*")) + list((ep / "成品").glob("*最终*"))
    final = None
    for f in final_candidates:
        if f.suffix in (".mp4", ".mkv"):
            final = f
            break
    
    if not final:
        issues.append("成品视频文件不存在")
        return issues
    
    # 1. File size check
    size_mb = os.path.getsize(final) / (1024 * 1024)
    if size_mb < 0.5:
        issues.append(f"视频文件过小: {size_mb:.1f}MB")
    else:
        print(f"  视频大小: {size_mb:.1f}MB")
    
    # 2. Video duration
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", str(final)
    ], capture_output=True, text=True, timeout=10)
    if r.stdout.strip():
        video_dur = float(r.stdout.strip())
        
        # Compare with timeline
        tl_path = ep / "timeline_v3.json"
        if tl_path.exists():
            with open(tl_path) as f:
                tl = json.load(f)
            tl_dur = tl.get("total_duration", 0)
            drift = abs(video_dur - tl_dur)
            if drift > 1.0:
                issues.append(f"视频时长偏差: timeline={tl_dur:.1f}s vs 实际={video_dur:.1f}s (差{drift:.1f}s)")
            else:
                print(f"  时长: timeline={tl_dur:.1f}s vs 实际={video_dur:.1f}s ✅")
    
    # 3. Audio check
    r = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(final)
    ], capture_output=True, text=True, timeout=10)
    if r.stdout.strip():
        print(f"  音频: {r.stdout.strip()} ✅")
    else:
        issues.append("无音频流")
    
    # 4. Subtitle check (for MKV with embedded subs)
    if final.suffix == ".mkv":
        r = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "s:0",
            "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(final)
        ], capture_output=True, text=True, timeout=10)
        if r.stdout.strip():
            print(f"  字幕: {r.stdout.strip()} ✅")
        else:
            print("  字幕: 未嵌入（外挂SRT可用）")
    
    # 5. Subtitle timing check (SRT file)
    srt_path = ep / "audio" / "narration.srt"
    if srt_path.exists() and r.stdout.strip():
        with open(srt_path, encoding="utf-8") as f:
            srt = f.read()
        # Find last segment's end time
        pattern = re.compile(r"(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})")
        matches = list(pattern.finditer(srt))
        if matches:
            last = matches[-1]
            end_str = last.group(2).replace(",", ".")
            parts = end_str.split(":")
            last_end = int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
            drift = abs(last_end - video_dur)
            if drift > 0.5:
                issues.append(f"字幕末句结束时间偏差: {last_end:.1f}s vs 视频{video_dur:.1f}s (差{drift:.1f}s)")
            else:
                print(f"  字幕末句: {last_end:.1f}s vs 视频 {video_dur:.1f}s ✅")
    
    return issues


if __name__ == "__main__":
    import sys
    ep = sys.argv[1] if len(sys.argv) > 1 else "."
    issues = check_video(ep)
    if issues:
        print(f"\n❌ {len(issues)} 个问题:")
        for i in issues:
            print(f"  - {i}")
    else:
        print(f"\n✅ 视频质量检查全部通过")
