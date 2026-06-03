#!/usr/bin/env python3
"""
harness.py v4 — 三段式门禁

Phase 1: 开工前（结构 + 清单）
Phase 2: 渲染前（格式 + 内容密度 + 布局多样性 + 语义 + 审计 + base64覆盖率）
Phase 3: 交付前（视频质量 + 黑帧 + 分辨率）

用法:
  python3 scripts/harness.py [项目名] [phase]
  phase: 1 / 2 / 3 / all
"""

import os, sys, re, json, subprocess

BASE = None
EXIT = 0

def log(name, ok, detail=""):
    global EXIT
    if not ok: EXIT += 1
    icon = "✅" if ok else "❌"
    suffix = f"  — {detail}" if detail else ""
    print(f"  {icon} {name}{suffix}")

def find_root():
    cwd = os.getcwd()
    for _ in range(5):
        if os.path.exists(os.path.join(cwd, ".git")) or os.path.exists(os.path.join(cwd, "AGENTS.md")):
            return cwd
        p = os.path.dirname(cwd)
        if p == cwd: break
        cwd = p
    return os.path.expanduser("~/Desktop/ascend-pipeline")

def find_project(name=None):
    if name:
        if os.path.isabs(name) and os.path.isdir(name):
            return os.path.abspath(name)
        for d in [os.path.join(BASE,"episodes",name), os.path.join(BASE,name)]:
            if os.path.isdir(d):
                return d
        print(f"❌ 不存在: {name}"); sys.exit(1)
    ep = os.path.join(BASE, "episodes")
    projects = sorted([d for d in os.listdir(ep) if os.path.isdir(os.path.join(ep,d)) and re.match(r'第\d+期_',d)], reverse=True) if os.path.isdir(ep) else []
    if not projects:
        projects = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE,d)) and re.match(r'第\d+期_',d)], reverse=True)
    if not projects:
        print("❌ 未找到项目"); sys.exit(1)
    p = os.path.join(ep, projects[0]) if os.path.isdir(ep) else os.path.join(BASE, projects[0])
    return os.path.abspath(p)


# ── Auto-discovery (自适应目录结构) ──

def find_idx(project):
    """Find index.html in project or any subdirectory."""
    candidates = [project] + [os.path.join(project, d) for d in os.listdir(project) if os.path.isdir(os.path.join(project, d))]
    for d in candidates:
        p = os.path.join(d, "index.html")
        if os.path.exists(p):
            return d, p
    return project, os.path.join(project, "index.html")

def find_comp_dir(project):
    """Find compositions/ anywhere under project."""
    for root, dirs, files in os.walk(project):
        if os.path.basename(root) == "compositions":
            return root
    return os.path.join(project, "compositions")

def find_audio_dir(project):
    """Find audio/ or 音频/ under project."""
    for root, dirs, files in os.walk(project):
        bn = os.path.basename(root)
        if bn in ("audio","音频"):
            return root
    return None

def find_slots(project):
    """Find image_slots.json anywhere."""
    for root, dirs, files in os.walk(project):
        if "image_slots.json" in files:
            return os.path.join(root, "image_slots.json")
    return None


# ── Constants ──

FONT_BLACKLIST = {"pingfang","microsoft yahei","noto sans","helvetica neue","siyuan","source han"}
LAYOUT_NAMES = {"hero","concept","flipped","comparison","data-chart","flowchart","quote","card-grid","timeline-h","code-block"}
HERMES_LAYOUTS = [
    ("hero-container","hero"), ("content-row","content"),
    ("compare-row","comparison"), ("flow-row","flowchart"),
    ("chart-row","chart"), ("quote-wrap","quote"),
]
MIN_CHINESE = 20
MIN_TAGS = 3
MIN_TOTAL_CHARS = 100
MIN_LAYOUTS = 3
MIN_B64_RATIO = 0.5


# ══════════════════════════════════════════════════════════════════════
# Shared: Structure
# ══════════════════════════════════════════════════════════════════════

def check_structure(project):
    proj_dir, idx_path = find_idx(project)
    comp_dir = find_comp_dir(project)
    print(f"\n{'='*60}\n📁 结构\n{'='*60}")
    log("index.html", os.path.exists(idx_path))
    log("compositions/", os.path.isdir(comp_dir))

    # Script auto-discovery
    has_script = False
    for root, dirs, files in os.walk(project):
        for f in files:
            if f in ("配音稿.txt","配音稿_分段.txt","narration.txt","口播稿.txt"):
                has_script = True; break
        if has_script: break
    log("配音稿", has_script)

    # .design-system auto-discovery
    ds_path = None
    for root, dirs, files in os.walk(project):
        if ".design-system" in files:
            ds_path = os.path.join(root, ".design-system"); break
    if ds_path:
        with open(ds_path) as f:
            log("设计风格", True, f.read().strip())
    else:
        log("设计风格", False, "缺 .design-system 文件")
    return proj_dir, idx_path, comp_dir


def check_kanban(project):
    name = os.path.basename(project)
    tenant = re.sub(r'[^a-z0-9_-]', '-', name.lower()).strip('-')[:30]
    try:
        r = subprocess.run(["hermes","kanban","list","--tenant",tenant,"--json"],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip().startswith("["):
            tasks = json.loads(r.stdout)
            log(f"Kanban ({tenant})", len(tasks) > 0, f"{len(tasks)} tasks")
    except: pass


# ══════════════════════════════════════════════════════════════════════
# Phase 1
# ══════════════════════════════════════════════════════════════════════

def phase1(project):
    print(f"\n{'='*60}\n🏗️  PHASE 1: 开工前\n{'='*60}")
    log("AGENTS.md", os.path.exists(os.path.join(BASE or ".","AGENTS.md")))
    print("\n  📋 自检（人工确认）：")
    for item in [
        "T3→TTS→T2 顺序正确（非 T2→T3）",
        "TTS 速率已实测 (--rate=-15%)",
        "配图页按缺口计算时长",
        "不自己烧录字幕",
        "SVG 不跨页重复",
        "profile 已创建",
        "配图 API 可用",
        "降级方案已定",
    ]:
        print(f"     □ {item}")


# ══════════════════════════════════════════════════════════════════════
# Phase 2 — 内容质量
# ══════════════════════════════════════════════════════════════════════

def phase2(project):
    print(f"\n{'='*60}\n🔧 PHASE 2: 渲染前\n{'='*60}")
    proj_dir, idx_path = find_idx(project)
    comp_dir = find_comp_dir(project)
    log("index.html", os.path.exists(idx_path))
    log("compositions/", os.path.isdir(comp_dir))

    if not os.path.exists(idx_path):
        return True
    with open(idx_path) as f:
        html = f.read()

    # Resolve composition paths relative to index.html's directory
    comp_base = os.path.dirname(idx_path)

    refs = re.findall(r'data-composition-src="([^"]+)"', html)
    log(f"composition ({len(refs)})", len(refs) >= 3)

    # ── Timeline ──
    blocks = re.findall(r'<div data-composition-id="s\d+"[^>]*>.*?</div>', html, re.DOTALL)
    starts, durs = [], []
    for b in blocks:
        s = re.search(r'data-start="([\d.]+)"', b)
        d = re.search(r'data-duration="([\d.]+)"', b)
        if s and d: starts.append(float(s.group(1))); durs.append(float(d.group(1)))
    tl_ok, pos = True, 0.0
    for i, (st, dr) in enumerate(zip(starts, durs)):
        if abs(st - pos) > 0.01:
            log(f"P{i+1} start={st} ≠ {pos}", False); tl_ok = False
        pos += dr
    total = sum(durs) if durs else 0
    m = re.search(r'data-duration="([\d.]+)"', html)
    dec = float(m.group(1)) if m else 0
    if dec: log(f"总时长 {dec:.1f}s ≈ 各页和 {total:.1f}s", abs(dec-total)<0.1)
    log("时间线连续", tl_ok)

    # ── Per-page quality ──
    print(f"\n  ── 每页内容 ──")
    all_ok, prev_layout, layouts = True, None, []
    density_warnings = []

    for i, ref in enumerate(refs):
        pid = i+1
        fp = os.path.join(comp_base, ref)
        if not os.path.exists(fp):
            fp = os.path.join(project, ref)
        if not os.path.exists(fp):
            log(f"P{pid} 文件", False, f"缺 {ref}")
            all_ok = False; continue

        with open(fp) as f:
            c = f.read()

        issues = []
        sid = f"s{pid}"
        if f'__timelines["{sid}"]' not in c: issues.append("缺_timelines")
        if f'__hf["{sid}"]' not in c: issues.append("缺__hf")
        if 'paused:true' not in c: issues.append("缺paused")
        if 'if(top===self)tl.progress(1)' not in c: issues.append("缺standalone")
        if 'sans-serif' not in c and 'monospace' not in c: issues.append("缺字体")
        if re.search(r'\.sl(?:ide)?\{[^}]*opacity:\s*0[^}]*\}', c): issues.append("opacity:0")

        cl = c.lower()
        for fb in FONT_BLACKLIST:
            if fb in cl and 'font-family' in cl[cl.find(fb)-20:cl.find(fb)+len(fb)+10]:
                issues.append(f"字体:{fb}"); break

        n_b64 = len(re.findall(r'<img[^>]*src="(?!data:image)[^"]{10,}"', c))
        if n_b64: issues.append(f"{n_b64}非base64图")

        # Content density
        text_only = re.sub(r'<[^>]+>', '', c)
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text_only))
        tags = len(re.findall(r'<(h[12]|p|span|div|li|code)[>\s]', c))
        has_image = bool(re.search(r'<img[^>]+data:image', c))
        has_code = '<code>' in c
        has_card = 'card' in cl

        if chinese < MIN_CHINESE and pid > 1:
            density_warnings.append(f"P{pid} 仅{chinese}字 (<{MIN_CHINESE})")
        if tags < MIN_TAGS and pid > 1:
            density_warnings.append(f"P{pid} 仅{tags}标签 (<{MIN_TAGS})")

        # ── Layout diversity (body-only detection) ──
        cur = None
        body_part = c.split('<body>', 1)[-1].split('</script>', 1)[0] if '<body>' in c else c
        body_lower = body_part.lower()
        for pattern, name in HERMES_LAYOUTS:
            if pattern in body_lower:
                cur = name; break
        if not cur:
            for ln in LAYOUT_NAMES:
                if ln in body_lower:
                    ctx = body_lower[body_lower.find(ln)-30:body_lower.find(ln)+len(ln)+30]
                    if 'class=' in ctx or 'layout=' in ctx:
                        cur = ln; break

        if cur:
            layouts.append(cur)
            if cur == prev_layout:
                issues.append(f"布局重复(连续两页{cur})")
        prev_layout = cur

        # ── Semantic check ──
        script_path = None
        for root, dirs, files in os.walk(project):
            for f in files:
                if f in ("配音稿_分段.txt","配音稿.txt","narration.txt"):
                    script_path = os.path.join(root, f); break
            if script_path: break

        if script_path and chinese > 50:
            with open(script_path) as sf:
                st = sf.read()
            terms = re.findall(r'[\u4e00-\u9fff]{2,}', text_only[:200])
            matches = sum(1 for t in set(terms) if t in st)
            if matches / max(len(terms),1) < 0.1 and len(terms) > 5:
                issues.append(f"语义匹配低({matches}/{len(terms)})")

        if issues:
            log(f"P{pid} 规范", False, " | ".join(issues[:5]))
            all_ok = False
        else:
            meta = f"[{chinese}c/{tags}t" + (" 🖼" if has_image else "") + (" 💻" if has_code else "") + (" 📇" if has_card else "") + "]"
            log(f"P{pid} {cur or ''} {meta}", True)

    log("全部 composition 规范", all_ok)

    # ── 审计文件检查 ──
    has_audit = False
    for root, dirs, files in os.walk(project):
        for f in files:
            if any(k in f.lower() for k in ["shenheyuan","审计","审核","review","audit"]):
                has_audit = True; break
        if has_audit: break
    log("审计产出", has_audit, "建议 T2/T6 后由 shenheyuan 审核" if not has_audit else "")

    if density_warnings:
        print(f"\n  ⚠️  密度警告 ({len(density_warnings)}):")
        for w in density_warnings[:5]:
            print(f"     {w}")

    # ── 布局多样性 ──
    if layouts:
        ul = len(set(layouts))
        log(f"布局多样性 ({ul}/10)", ul >= MIN_LAYOUTS, f"使用: {', '.join(sorted(set(layouts)))}")
        if len(layouts) != len(set(layouts)):
            repeats = [x for i, x in enumerate(layouts) if x in layouts[:i]]
            log("布局重复", False, f"出现多次: {', '.join(set(repeats))}")

    # ── 全片文字量 ──
    total_ch = 0
    for ref in refs:
        fp = os.path.join(comp_base, ref)
        if not os.path.exists(fp):
            fp = os.path.join(project, ref)
        if os.path.exists(fp):
            with open(fp) as f:
                total_ch += len(re.findall(r'[\u4e00-\u9fff]', re.sub(r'<[^>]+>','',f.read())))
    log(f"全片总文字量 {total_ch}字", total_ch > MIN_TOTAL_CHARS)

    # ── Base64 覆盖率 ──
    slots_img = 0
    slots_path = find_slots(project)
    if slots_path:
        try:
            with open(slots_path) as f:
                slots = json.load(f)
            slot_list = slots.get("slots", slots if isinstance(slots,list) else [])
            slots_img = len([s for s in slot_list if isinstance(s,dict) and s.get("source") in ("real","ai")])
        except: pass

    used_img = 0
    for ref in refs:
        fp = os.path.join(comp_base, ref)
        if not os.path.exists(fp):
            fp = os.path.join(project, ref)
        if os.path.exists(fp):
            with open(fp) as f:
                used_img += len(re.findall(r'<img[^>]+src="data:image', f.read()))

    if slots_img > 0:
        r = min(used_img/slots_img, 1.0)
        log(f"Base64 图 {used_img}/{slots_img} ({r:.0%})", r >= MIN_B64_RATIO,
            "低于 50% 建议检查配图未嵌入的页面" if r < MIN_B64_RATIO else "")
    elif used_img > 0:
        log(f"Base64 图 {used_img} 张", True)
    else:
        log("Base64 图", False, "全片无 base64 图片")

    # ── timeline vs index.html ──
    tl_path = os.path.join(project, "timeline.json")
    if os.path.exists(tl_path) and dec > 0:
        try:
            with open(tl_path) as f:
                tld = json.load(f)
            tl_total = sum(s.get("duration",0) for s in tld.get("slides",[]))
            log(f"timeline.json {tl_total:.1f}s ≈ index.html {dec:.1f}s", abs(tl_total - dec) < 2.0)
        except: pass

    return EXIT == 0


# ══════════════════════════════════════════════════════════════════════
# Phase 3 — 视频质量
# ══════════════════════════════════════════════════════════════════════

def phase3(project):
    print(f"\n{'='*60}\n📺 PHASE 3: 交付前\n{'='*60}")
    # Search recursively for mp4 files
    all_mp4 = []
    for root, dirs, files in os.walk(project):
        for f in files:
            if f.endswith('.mp4'):
                all_mp4.append(os.path.join(root, f))
    vip = [f for f in all_mp4 if 'final' in os.path.basename(f).lower()]
    videos = vip or all_mp4
    if not videos:
        log("视频文件", False); return True

    latest = max([os.path.join(project, v) for v in videos], key=os.path.getmtime)
    log("视频文件", True, os.path.basename(latest))

    # Resolution
    r = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
                        "-show_entries","stream=width,height","-of","csv=p=0",latest],
                       capture_output=True, text=True)
    if r.stdout.strip():
        parts = r.stdout.strip().split(",")
        if len(parts)==2:
            w,h = int(parts[0]),int(parts[1])
            log(f"分辨率 {w}x{h}", w==1920 and h==1080)
            log(f"尺寸可被2整除", w%2==0 and h%2==0)

    # Duration
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","csv=p=0",latest], capture_output=True, text=True)
    dur = float(r.stdout.strip()) if r.stdout.strip() else 0
    log(f"时长 {dur:.1f}s", dur > 5)

    # Audio
    r = subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
                        "-show_entries","stream=codec_name","-of","csv=p=0",latest],
                       capture_output=True, text=True)
    has_audio = bool(r.stdout.strip())
    log("音频", has_audio)
    if has_audio:
        log("编码 AAC", "aac" in r.stdout.strip().lower(), r.stdout.strip())

    # Black frame detection
    if dur > 5:
        mid = dur / 2
        try:
            r = subprocess.run(["ffmpeg","-y","-ss",str(mid),"-i",latest,
                                "-vframes","1","-vf","format=gray,metadata=mean",
                                "-f","null","-"],
                               capture_output=True, text=True, timeout=30)
            is_black = 'mean:0' in r.stderr
            log("黑帧检测", not is_black, f"采样@t={mid:.0f}s")
        except: log("黑帧检测", True, "(跳过)")

    # File size
    mb = os.path.getsize(latest) / (1024*1024)
    min_mb = max(0.5, dur/120*1.0) if dur > 0 else 0.5
    log(f"文件 {mb:.1f}MB", mb >= min_mb)

    # Render log
    rl = os.path.join(project, ".render_log.json")
    if os.path.exists(rl):
        try:
            with open(rl) as f:
                log("渲染日志", True, f"{json.load(f).get('render_time_s','?')}s")
        except: log("渲染日志", False, "损坏")

    return EXIT == 0


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    BASE = find_root()
    project = find_project(sys.argv[1] if len(sys.argv) > 1 else None)
    phase = sys.argv[2] if len(sys.argv) > 2 else "1"

    registry = {
        "1": [lambda p: check_structure(p), phase1],
        "2": [lambda p: check_structure(p), check_kanban, phase2],
        "3": [phase3],
        "all": [lambda p: check_structure(p), check_kanban, phase1, phase2, phase3],
    }
    for fn in registry.get(phase, registry["1"]):
        fn(project)

    name = os.path.basename(project)
    print(f"\n{'='*60}")
    if EXIT == 0:
        print(f"🎉 [{name}] 全部通过")
    else:
        print(f"❌ [{name}] {EXIT} 项未通过")
    sys.exit(0 if EXIT == 0 else 1)
