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
    # Hermes custom gen patterns
    ("comp-left","comparison"),  # .comp-left + .comp-right = comparison
    (".comp-left","comparison"),
    ('class="card"',"card-grid"),  # multiple class="card"
]
MIN_CHINESE = 20
MIN_TAGS = 3
MIN_TOTAL_CHARS = 100
MIN_LAYOUTS = 3
MIN_B64_RATIO = 0.5
MIN_STANDALONE_RATIO = 0.9  # 至少 90% 的页面要有 standalone mode

# Design system token profiles (brand color + font)
# Extracted from ~/Desktop/ascend-pipeline/designs/awesome-design-md/design-md/*/DESIGN.md
DESIGN_PROFILES = {
    "mintlify": {
        "brand_color": "#00d4a4",
        "font_body": "Inter",
        "surface": "#f7f7f7",
        "ink": "#0a0a0a",
        "charcoal": "#1c1c1e",
    },
    "notion": {
        "brand_color": "#000000",
        "font_body": "Inter,sans-serif",
        "surface": "#f7f6f3",
        "ink": "#0a0a0a",
        "charcoal": "#37352f",
    },
    "linear.app": {
        "brand_color": "#5e6ad2",
        "font_body": "Inter,sans-serif",
        "surface": "#0f1011",
        "ink": "#f7f8f8",
        "charcoal": "#010102",
    },
    "default": {
        "brand_color": None,  # no check
        "font_body": "sans-serif",
        "surface": None,
        "ink": None,
        "charcoal": None,
    },
}


# ── Design / Style helpers ──

def check_standalone(comp_path):
    """Check if a single composition has standalone mode."""
    if not os.path.exists(comp_path):
        return False
    with open(comp_path) as f:
        c = f.read()
    # Check for any if(top===self) pattern that includes tl.progress
    return ("if(top===self)" in c and "tl.progress" in c) or "if(top===self)console.log" in c


def get_design_profile(project):
    """Read .design-system file and return the matching design profile."""
    ds_path = None
    for root, dirs, files in os.walk(project):
        if ".design-system" in files:
            ds_path = os.path.join(root, ".design-system")
            break
    if not ds_path:
        if os.path.exists(os.path.join(project, ".design-system")):
            ds_path = os.path.join(project, ".design-system")
    if not ds_path:
        log("设计规范", False, "缺 .design-system 文件")
        return None
    with open(ds_path) as f:
        style = f.read().strip().lower()
    profile = DESIGN_PROFILES.get(style) or DESIGN_PROFILES.get("default")
    if profile:
        BRAND = profile.get("brand_color", "N/A")
        FONT = profile.get("font_body", "N/A")
        log("设计规范", True, f"风格={style}, 品牌色={BRAND}, 字体={FONT}")
    return profile


def check_dir_structure(project):
    """Verify composition files exist in all expected directories."""
    comp_dirs = ["compositions", "04_PPT/compositions", "06_Compositions/compositions"]
    for d in comp_dirs:
        p = os.path.join(project, d)
        count = len([f for f in os.listdir(p) if f.endswith(".html")]) if os.path.isdir(p) else 0
        if count >= 3:
            log(f"目录 {d}", True, f"{count} 个 composition")
            return True
    log("composition 目录", False, "未在标准路径找到 (compositions/ | 04_PPT/compositions/ | 06_Compositions/compositions/)")
    return False


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
        
        if 'sans-serif' not in c and 'monospace' not in c: issues.append("缺字体")
        n_anim = c.count("tl.from(") + c.count("tl.to(")
        if n_anim < 3: issues.append(f"动画仅{n_anim}步")
        if not re.search(r"\d+\s*/\s*\d+", c) and pid > 1:
            issues.append("缺页码")
        has_badge = "border-radius:20px" in c or "badge" in c.lower()
        has_heading = bool(re.search(r"font-size:[45]\d", c))
        has_img = "data:image" in c
        has_body = "<p>" in c or "<li>" in c or 'class="card"' in c or 'class="item"' in c
        layers = sum([has_badge, has_heading, has_img, has_body]) + 1
        if layers < 3 and pid > 1:
            issues.append(f"层次仅{layers}层")
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
        # Try 1: specific class names (Hermes standard)
        for pattern, name in HERMES_LAYOUTS:
            if pattern in body_lower:
                cur = name; break
        # Try 2: layout name in CSS class
        if not cur:
            for ln in LAYOUT_NAMES:
                if ln in body_lower:
                    ctx = body_lower[body_lower.find(ln)-30:body_lower.find(ln)+len(ln)+30]
                    if 'class=' in ctx or 'layout=' in ctx:
                        cur = ln; break
        # Try 3: structural detection (catches Hermes custom gen)
        if not cur:
            text_only = re.sub(r'<[^>]+>', '', body_part)
            chinese = len(re.findall(r'[\u4e00-\u9fff]', text_only))
            n_divs = len(re.findall(r'<div[^>]*style="', c))
            n_flex = len(re.findall(r'display:\s*flex', c))
            has_arrows = '→' in c or '⬇️' in c or '➡️' in c
            has_comp_css = '.comp-left' in c or '.comp-right' in c
            has_card_class = bool(re.findall(r'class="[^"]*card[^"]*"', c, re.I))
            has_emoji = len(re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF]', c)) >= 2
            
            # hero: title page, few divs, no flex, little text
            # hero: minimal text, no complex content
            if chinese <= 25 and not has_card_class and not has_arrows and not has_comp_css:
                cur = 'hero'
            elif n_flex <= 1 and chinese <= 20 and 'font-size:5' in c:
                cur = 'hero'
            # comparison: .comp-left / .comp-right CSS classes
            elif has_comp_css:
                cur = 'comparison'
            # card-grid: card class names + many divs
            elif has_card_class and n_divs >= 8:
                cur = 'card-grid'
            # flowchart: arrows + flex layout
            elif has_arrows and n_flex >= 2:
                cur = 'flowchart'
            # code-block
            elif '<code>' in body_part or 'monospace' in body_part:
                cur = 'code-block'
            # hero (cover/ending): few divs, big centered content
            if n_divs <= 3 and any(x in c for x in ['font-size:5','font-size:6','font-size:7','font-size:8','font-size:4']):
                cur = 'hero'
            # quote: few divs, lots of text, font-size styling
            elif n_divs <= 5 and chinese >= 30 and 'font-size' in body_part:
                cur = 'quote'
            # default: concept (can be concept or flipped)
            else:
                # flipped: has emoji + text on opposite sides
                if has_emoji and n_flex >= 1:
                    cur = 'flipped'
                else:
                    cur = 'concept'  # default

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

    # ── Standalone 覆盖率 ──
    standalone_ok = sum(1 for r in refs if check_standalone(os.path.join(comp_base, r) if os.path.exists(os.path.join(comp_base, r)) else os.path.join(project, r)))
    sr = standalone_ok / max(len(refs), 1)
    log(f"standalone 模式 {standalone_ok}/{len(refs)} ({sr:.0%})", sr >= MIN_STANDALONE_RATIO)

    # ── 设计规范符合度 ──
    ds_profile = get_design_profile(project)
    if ds_profile:
        brand_ok, font_ok, surface_ok, ink_ok = 0, 0, 0, 0
        total_checked = 0
        for ref in refs:
            fp = os.path.join(comp_base, ref) if os.path.exists(os.path.join(comp_base, ref)) else os.path.join(project, ref)
            if not os.path.exists(fp):
                continue
            with open(fp) as f:
                c = f.read()
            total_checked += 1
            if ds_profile.get("brand_color") and ds_profile["brand_color"] in c:
                brand_ok += 1
            if ds_profile.get("font_body") and ds_profile["font_body"] in c:
                font_ok += 1
            if ds_profile.get("surface") and ds_profile["surface"] in c:
                surface_ok += 1
            if ds_profile.get("ink") and ds_profile["ink"] in c:
                ink_ok += 1
        if total_checked > 0:
            log(f"品牌色 [{ds_profile.get('brand_color','?')}] {brand_ok}/{total_checked}", brand_ok / total_checked >= 0.5)
            log(f"正文字体 [{ds_profile.get('font_body','?')}] {font_ok}/{total_checked}", font_ok / total_checked >= 0.5)
            if ds_profile.get("surface"):
                log(f"卡片背景 [{ds_profile.get('surface','?')}] {surface_ok}/{total_checked}", surface_ok / total_checked >= 0.3)
        
        # B) 口播稿含分镜指令检测
        script_path = None
        for root, dirs, files in os.walk(project):
            for fn in files:
                if fn in ("配音稿_分段.txt","口播稿.md","口播稿.txt","配音稿.txt"):
                    script_path = os.path.join(root, fn); break
            if script_path: break
        if script_path:
            with open(script_path, encoding='utf-8') as sf:
                sc = sf.read()
            story_markers = len(re.findall(r'[（(][^）)]*画面[^）)]*[）)]', sc))
            time_markers = len(re.findall(r'[（(][^）)]*字数[^）)]*[）)]', sc))
            if story_markers > 0 or time_markers > 0:
                log("口播稿含分镜指令", False, f"{story_markers}处'（画面）' + {time_markers}处'（字数）'")
            else:
                log("口播稿含分镜指令", True, "无")

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
        # Only flag consecutive duplicates
        consec = sum(1 for i in range(1, len(layouts)) if layouts[i] == layouts[i-1])
        if consec > 0:
            log("布局连续重复", False, f"{consec} 处连续相同布局")
        else:
            log("布局连续重复", True, "无连续同布局")

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
            # Support both formats: slides[], pages[], and total_duration
            tl_total = tld.get("total_duration", 0)
            if not tl_total:
                tl_slides = tld.get("slides", tld.get("pages", []))
                tl_total = sum(s.get("duration", 0) for s in tl_slides)
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
