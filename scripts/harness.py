#!/usr/bin/env python3
"""
pipeline-harness
================
三段式管线门禁：开工前 → 渲染前 → 交付前
每段一个命令，过不去就停下。
"""

import os, sys, re, json, subprocess

BASE = None  # 自动检测

def find_repo_root():
    """从当前目录向上找，直到找到 .git 或 AGENTS.md"""
    cwd = os.getcwd()
    for _ in range(5):
        if os.path.exists(os.path.join(cwd, ".git")) or os.path.exists(os.path.join(cwd, "AGENTS.md")):
            return cwd
        parent = os.path.dirname(cwd)
        if parent == cwd:
            break
        cwd = parent
    return os.path.expanduser("~/Desktop/ascend-pipeline")  # fallback
EXIT = 0

def log(name, ok, detail=""):
    global EXIT
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        EXIT = 1

def get_project(name=None):
    if name:
        p = os.path.join(BASE, name)
        if os.path.isdir(p): return p
        print(f"❌ 项目不存在: {name}")
        sys.exit(1)
    projects = sorted([d for d in os.listdir(BASE) 
                      if os.path.isdir(os.path.join(BASE, d)) and re.match(r'第\d+期_', d)], reverse=True)
    if not projects:
        print("❌ 没找到项目")
        sys.exit(1)
    return os.path.join(BASE, projects[0])


def phase1_preflight(project):
    """段1: 开工前检查——做对事"""
    print(f"\n{'='*60}\n🏗️  PHASE 1: 开工前检查\n{'='*60}")
    
    # 1. AGENTS.md存在
    agents = os.path.join(BASE, "AGENTS.md")
    log("AGENTS.md 存在", os.path.exists(agents))
    
    # 2. 设计风格已选（design-system标记文件）
    ds_marker = os.path.join(project, ".design-system")
    if os.path.exists(ds_marker):
        with open(ds_marker) as f:
            style = f.read().strip()
        log("设计风格已选", True, style)
    else:
        log("设计风格已选", False, "缺少 .design-system 文件")
    
    # 3. 口播稿已写（T3完成标记）
    script_files = ['口播稿.txt', '配音稿.txt', '配音稿_分段.txt', 'narration.txt']
    has_script = any(os.path.exists(os.path.join(project, f)) for f in script_files)
    log("口播稿已写 (T3)", has_script)
    
    # 4. 开工检查清单
    print("\n  📋 开工清单（人工确认）：")
    checks = [
        "所有需要的profile已创建",
        "配图API可用性已验证",
        "TTS语速参数已确认（当前: atempo=1.15x）",
        "降级方案已确定",
    ]
    for c in checks:
        print(f"     □ {c}")
    print("  请逐条手动确认后再继续")
    
    return EXIT == 0


def phase2_prerender(project):
    """段2: 渲染前检查——做对文件"""
    print(f"\n{'='*60}\n🔧 PHASE 2: 渲染前检查\n{'='*60}")
    
    idx_path = os.path.join(project, "index.html")
    comp_dir = os.path.join(project, "compositions")
    
    log("index.html 存在", os.path.exists(idx_path))
    log("compositions/ 存在", os.path.isdir(comp_dir))
    
    if not os.path.exists(idx_path):
        return False
    
    # 解析index.html
    with open(idx_path) as f:
        idx = f.read()
    
    refs = re.findall(r'data-composition-src="([^"]+)"', idx)
    log(f"composition引用数({len(refs)}) >= 3", len(refs) >= 3)
    
    # 时间线连续性
    blocks = re.findall(r'<div data-composition-id="s\d+".*?</div>', idx)
    starts, durs = [], []
    for b in blocks:
        s = re.search(r'data-start="([^"]+)"', b)
        d = re.search(r'data-duration="([^"]+)"', b)
        if s and d:
            starts.append(float(s.group(1)))
            durs.append(float(d.group(1)))
    
    timeline_ok = True
    pos = 0.0
    for i, (st, dr) in enumerate(zip(starts, durs)):
        if abs(st - pos) > 0.01:
            log(f"P{i+1} start={st} ≠ 期望{pos}", False)
            timeline_ok = False
        pos += dr
    total = sum(durs)
    
    m = re.search(r'data-duration="([\d.]+)"', idx)
    declared = float(m.group(1)) if m else 0
    if declared:
        log(f"总时长 {declared:.1f}s = 各页之和 {total:.1f}s", abs(declared - total) < 0.1)
    
    log("时间线连续无间隙", timeline_ok)
    
    # 每个composition文件
    all_comp_ok = True
    for i, ref in enumerate(refs):
        pid = i + 1
        fpath = os.path.join(project, ref)
        if not os.path.exists(fpath):
            log(f"P{pid} 文件存在", False, f"缺{ref}")
            all_comp_ok = False
            continue
        
        with open(fpath) as f:
            c = f.read()
        
        issues = []
        sid = f"s{pid}"
        if f'data-composition-id="{sid}"' not in c: issues.append("缺ID")
        if 'data-width="1920"' not in c: issues.append("缺W")
        if 'data-height="1080"' not in c: issues.append("缺H")
        if 'gsap.min.js' not in c: issues.append("缺GSAP")
        if 'paused:true' not in c: issues.append("缺paused")
        if f'__timelines["{sid}"]' not in c: issues.append("缺tl")
        if f'__hf["{sid}"]' not in c: issues.append("缺hf")
        if 'sans-serif' not in c and 'monospace' not in c: issues.append("缺字体")
        if re.search(r'\.slide\{[^}]*opacity:\s*0[^}]*\}', c): issues.append("opacity:0致命")
        
        if issues:
            log(f"P{pid} 规范检查", False, " | ".join(issues))
            all_comp_ok = False
        else:
            log(f"P{pid} 规范检查", True)
    
    log("全部composition规范正确", all_comp_ok)
    
    # hyperframes lint
    r = subprocess.run(["hyperframes", "lint", project], capture_output=True, text=True, cwd=project)
    errors = r.stdout.count("✗")
    log("hyperframes lint 0 error", errors == 0, f"{errors} errors" if errors else "")
    
    return EXIT == 0


def phase3_postrender(project):
    """段3: 交付前检查——做对结果"""
    print(f"\n{'='*60}\n📺 PHASE 3: 交付前检查\n{'='*60}")
    
    # 找最新渲染的视频
    videos = [f for f in os.listdir(project) if f.endswith('.mp4') and 'final' in f.lower()]
    if not videos:
        videos = [f for f in os.listdir(project) if f.endswith('.mp4')]
    
    if not videos:
        log("视频文件存在", False)
        return False
    
    latest = max([os.path.join(project, v) for v in videos], key=os.path.getmtime)
    log("视频文件存在", True, os.path.basename(latest))
    
    # 检查视频时长
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", latest], capture_output=True, text=True)
    if r.stdout.strip():
        video_dur = float(r.stdout.strip())
        log(f"视频长度 {video_dur:.1f}s", video_dur > 10)
    
    # 检查是否有音频流
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=codec_name", "-of", "csv=p=0", latest],
                       capture_output=True, text=True)
    has_audio = bool(r.stdout.strip())
    log("视频包含音频流", has_audio)
    
    return EXIT == 0


if __name__ == "__main__":
    BASE = find_repo_root()
    project = get_project(sys.argv[1] if len(sys.argv) > 1 else None)
    proj_name = os.path.basename(project)
    
    phase = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    if phase == "1":
        phase1_preflight(project)
    elif phase == "2":
        phase2_prerender(project)
    elif phase == "3":
        phase3_postrender(project)
    else:
        # 默认跑全三段，但phase3没视频不致命（可能是新项目还没渲染）
        phase1_preflight(project)
        phase2_prerender(project)
        phase3_postrender(project)
        if EXIT > 0:
            # 检查phase3是否唯一失败项
            pass  # 允许用户自行判断
    
    print(f"\n{'='*60}")
    if EXIT == 0:
        print(f"🎉 [{proj_name}] 全部通过")
    else:
        print(f"❌ [{proj_name}] 有{EXIT}项失败")
    
    sys.exit(EXIT)
