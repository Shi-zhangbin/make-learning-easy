#!/usr/bin/env python3
"""
render_perf_log.py — 渲染性能日志

在 T7 渲染完成后调用，记录指标到 .render_log.json。

用法:
  python3 scripts/render_perf_log.py episodes/第N期_xxx --render-time 900
  python3 scripts/render_perf_log.py episodes/第N期_xxx --render-time 1200 --errors "timeout"
  python3 scripts/render_perf_log.py episodes/第N期_xxx --show
"""

import argparse, json, os, re, subprocess, sys
from datetime import datetime

def collect(project, render_time=0, success=True, errors=""):
    idx = os.path.join(project, "index.html")
    m = {"ts":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "project":os.path.basename(project),
         "compositions":0, "total_duration":0.0, "render_time_s":render_time,
         "success":success, "errors":errors, "video_size_mb":0, "video_duration_s":0.0, "audio_present":False}
    if os.path.exists(idx):
        with open(idx) as f:
            h = f.read()
        m["compositions"] = len(re.findall(r'data-composition-src=', h))
        d = re.search(r'data-duration="([\d.]+)"', h)
        if d: m["total_duration"] = float(d.group(1))
    videos = sorted([f for f in os.listdir(project) if f.endswith('.mp4')], reverse=True)
    if videos:
        vip = [v for v in videos if 'final' in v.lower()]
        latest = max([os.path.join(project, v) for v in (vip or videos)], key=os.path.getmtime)
        m["video_size_mb"] = round(os.path.getsize(latest)/(1024*1024), 1)
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",latest], capture_output=True, text=True)
        if r.stdout.strip(): m["video_duration_s"] = round(float(r.stdout.strip()), 1)
        r = subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_name","-of","csv=p=0",latest], capture_output=True, text=True)
        if r.stdout.strip(): m["audio_present"] = True
    return m

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project"); p.add_argument("--render-time", type=int, default=0)
    p.add_argument("--success", type=bool, default=True); p.add_argument("--errors", default="")
    p.add_argument("--show", action="store_true")
    args = p.parse_args()
    if not os.path.isdir(args.project):
        print(f"❌ 不存在: {args.project}"); sys.exit(1)
    lp = os.path.join(args.project, ".render_log.json")
    if args.show:
        if os.path.exists(lp):
            with open(lp) as f: print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
        else: print("ℹ️  无日志")
        return
    m = collect(args.project, args.render_time, args.success, args.errors)
    history = []
    if os.path.exists(lp):
        try:
            e = json.load(open(lp)); history = [e] if isinstance(e, dict) else e
        except: pass
    history.append(m)
    with open(lp, "w") as f: json.dump(history if len(history)>1 else m, f, ensure_ascii=False, indent=2)
    print(f"💾 {lp}")

if __name__ == "__main__":
    main()
