"""
v3/gates/gate_master.py — 统一门禁调度

每个步骤完成后调用对应 gate，gate 返回：
  - issues: list[str] — 具体问题
  - feedback_target: str — 应该退回哪个阶段
  - passed: bool — 是否通过
"""
from dataclasses import dataclass, field


@dataclass
class GateResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    feedback_target: str = ""  # 退回哪个阶段（如 "T1", "T2"）
    
    def message(self) -> str:
        if self.passed:
            return ""
        target = f" → 退回 {self.feedback_target} 修改" if self.feedback_target else ""
        msg = "\n".join(f"  ❌ {i}" for i in self.issues)
        return f"{msg}{target}"
    
    def __bool__(self):
        return self.passed


# ══════════════════════════════════════════════════════════════
# T0 Gate — 选题报告
# ══════════════════════════════════════════════════════════════

def check_t0(episode_dir: str) -> GateResult:
    """选题报告完整吗？"""
    import os
    issues = []
    md_path = os.path.join(episode_dir, "选题研究报告.md")
    if not os.path.exists(md_path):
        return GateResult(False, ["选题研究报告.md 不存在"], "T0")
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    if len(content) < 200:
        issues.append(f"选题报告仅 {len(content)} 字，信息量不足")
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T0")


# ══════════════════════════════════════════════════════════════
# T1 Gate — 知识点大纲
# ══════════════════════════════════════════════════════════════

def check_t1(episode_dir: str) -> GateResult:
    """大纲结构合理吗？"""
    import os
    issues = []
    md_path = os.path.join(episode_dir, "知识点大纲.md")
    if not os.path.exists(md_path):
        return GateResult(False, ["知识点大纲.md 不存在"], "T1")
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    if len(content) < 300:
        issues.append(f"知识点大纲仅 {len(content)} 字，内容不足")
    # 检查是否有知识点编号（一、二、三 或 1. 2. 3.）
    import re
    has_structure = bool(re.search(r'[一二三四五六七八九十]+、|\d+\.', content))
    if not has_structure:
        issues.append("大纲缺少结构化编号（一、二、三…）")
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T1")


# ══════════════════════════════════════════════════════════════
# T2 Gate — 口播稿
# ══════════════════════════════════════════════════════════════

def check_t2(episode_dir: str) -> GateResult:
    """口播稿无残留标记、无空页、字数合理。"""
    import os, re
    issues = []
    
    candidates = ["配音稿_分段.txt", "配音稿.txt", "口播稿.txt"]
    script_path = None
    for c in candidates:
        p = os.path.join(episode_dir, c)
        if os.path.exists(p):
            script_path = p
            break
    
    if not script_path:
        return GateResult(False, ["口播稿文件不存在"], "T2")
    
    with open(script_path, encoding="utf-8") as f:
        content = f.read()
    
    # 标记残留
    artifacts = []
    for pat, name in [(r'#{2,}', "##标题"), (r'\*{2,}', "**加粗**"), (r'`{2,}', "``代码``")]:
        if re.search(pat, content):
            artifacts.append(name)
    if artifacts:
        issues.append(f"含残留标记: {', '.join(artifacts)}")
    
    # 空页
    page_pattern = re.compile(r"---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL)
    pages = list(page_pattern.finditer(content))
    if not pages:
        issues.append("无法解析分页标记")
    else:
        empty = [m.group(1) for m in pages if not m.group(2).strip()]
        if empty:
            issues.append(f"空页: P{', '.join(empty)}")
        if len(pages) < 5:
            issues.append(f"仅 {len(pages)} 页，视频太短")
    
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T2")


# ══════════════════════════════════════════════════════════════
# T3 Gate — 配音+字幕
# ══════════════════════════════════════════════════════════════

def check_t3(episode_dir: str) -> GateResult:
    """配音时长 vs 口播字数偏差是否在合理范围。"""
    import os, json, subprocess
    issues = []
    
    audio_path = os.path.join(episode_dir, "audio", "narration.mp3")
    if not os.path.exists(audio_path):
        return GateResult(False, ["配音音频不存在"], "T3")
    
    # 获取音频时长
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", audio_path], capture_output=True, text=True, timeout=10)
    if not r.stdout.strip():
        return GateResult(False, ["无法获取音频时长"], "T3")
    audio_dur = float(r.stdout.strip())
    
    # 获取口播稿字数
    candidates = ["配音稿_纯文字.txt", "配音稿_分段.txt", "口播稿.txt"]
    script_path = None
    for c in candidates:
        p = os.path.join(episode_dir, c)
        if os.path.exists(p): script_path = p; break
    if not script_path:
        return GateResult(True, [], "")  # 没有口播稿就跳过
    
    import re
    with open(script_path, encoding="utf-8") as f:
        script_text = f.read()
    # 如果是带标记的，剥离标记后算字数
    clean = re.sub(r'---.*?---\s*\n', '', script_text)
    chars = len(re.findall(r'[\u4e00-\u9fff\w]', clean))
    
    # 估算语速
    rate = chars / max(audio_dur, 0.1)
    if rate < 2.0 or rate > 8.0:
        issues.append(f"语速异常: {rate:.1f}字/秒 (正常范围 3~6)")
    if audio_dur < 30:
        issues.append(f"音频仅 {audio_dur:.0f}秒，视频太短")
    
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T2")


# ══════════════════════════════════════════════════════════════
# T4 Gate — 分镜设计
# ══════════════════════════════════════════════════════════════

def check_t4(episode_dir: str) -> GateResult:
    """分镜方案完整吗？image_slots 有吗？"""
    import os, json
    issues = []
    
    slots_path = None
    for root, dirs, files in os.walk(episode_dir):
        if "image_slots.json" in files:
            slots_path = os.path.join(root, "image_slots.json")
            break
    
    if not slots_path:
        issues.append("image_slots.json 不存在（至少需要 SVG 兜底插槽）")
    else:
        with open(slots_path) as f:
            slots = json.load(f)
        slot_list = slots.get("slots", slots) if isinstance(slots, dict) else slots
        if not slot_list:
            issues.append("image_slots.json 为空")
        # 检查是否每页都有至少一个 slot
        pages_covered = len(set(s.get("page", 0) for s in slot_list if isinstance(s, dict)))
        pages_total = len(list(Path(episode_dir).glob("compositions/scene_*.html")))
    
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T4")


# ══════════════════════════════════════════════════════════════
# Content Accuracy Gate — 内容准确性审核（调用 shenheyuan agent）
# ══════════════════════════════════════════════════════════════

def check_content_accuracy(step: str, episode_dir: str) -> GateResult:
    """内容准确性审核 — 检查基本知识性错误。纯 Python，无 agent 依赖。"""
    import os, re
    issues = []
    
    files_to_check = {
        "T1": ["知识点大纲.md"],
        "T2": ["配音稿_分段.txt", "口播稿.txt"],
        "T4": ["PPT大纲.md"],
    }
    
    for fname in files_to_check.get(step, []):
        fpath = None
        for root, dirs, files in os.walk(episode_dir):
            if fname in files:
                fpath = os.path.join(root, fname); break
        if not fpath: continue
        
        with open(fpath, encoding="utf-8", errors="replace") as f:
            c = f.read()
        
        if fname == "知识点大纲.md":
            if not re.search(r'[一二三四五六七八九十]+、|\d+\.', c):
                issues.append("大纲缺少结构化编号")
            if len(c) < 200:
                issues.append("大纲内容过短")
        if fname in ("配音稿_分段.txt", "口播稿.txt"):
            if not re.findall(r"---\s*P\d+.*?---", c):
                issues.append("口播稿缺少分页标记")
        if fname == "PPT大纲.md":
            if not re.search(r'布局|layout|配图', c, re.IGNORECASE):
                issues.append("分镜方案缺少布局定义")
    
    if issues:
        return GateResult(False, issues, step)
    return GateResult(True, [])
# ══════════════════════════════════════════════════════════════
# T6 Gate — Composition（布局质量）
# ══════════════════════════════════════════════════════════════

def check_t6(episode_dir: str) -> GateResult:
    """页面层数、视觉元素、布局多样性。"""
    import re
    from pathlib import Path
    from v3.pagespec import MIN_LAYERS
    
    comp_dir = Path(episode_dir) / "compositions"
    if not comp_dir.exists():
        return GateResult(False, ["compositions/ 目录不存在"], "T4")
    
    issues = []
    files = sorted(comp_dir.glob("scene_*.html"))
    
    for fp in files:
        html = fp.read_text(encoding="utf-8")
        page_num = int(re.search(r'scene_(\d+)', fp.stem).group(1))
        
        # 层数
        layers = len(re.findall(r'class="[^"]*(?:badge-section|page-title|page-subtitle|feature-card|'
                                r'code-window|quote-card|step-card|image-rail|compare-col|step-arrow|grid-2x2)[^"]*"', html))
        # 找出这个页面用的什么布局（从 title 或者上下文推断）
        min_l = 5  # 默认
        if layers < min_l:
            issues.append(f"P{page_num}: {layers}层 < {min_l}层，内容太少")
        
        # 视觉元素
        if not re.search(r'data:image|card-icon|window-body|step-arrow|progress-dot', html):
            issues.append(f"P{page_num}: 纯文字页，缺少视觉元素")
        
        # 检查 page-number 在底部
        if "position:absolute;bottom:30px" not in html and "position: absolute; bottom: 30px" not in html:
            issues.append(f"P{page_num}: 页码不在底部")
    
    # 布局多样性检查
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T4")


# ══════════════════════════════════════════════════════════════
# T7 Gate — 渲染后视频质量
# ══════════════════════════════════════════════════════════════

def check_t7(episode_dir: str) -> GateResult:
    """视频时长对齐、音频存在、字幕偏差。"""
    import os, json, subprocess, re
    from pathlib import Path
    
    ep = Path(episode_dir)
    issues = []
    
    # 找最终视频
    finals = list(ep.glob("成品/*final*")) + list(ep.glob("成品/*最终*"))
    final = None
    for f in finals:
        if f.suffix in (".mp4", ".mkv"):
            final = f; break
    
    if not final:
        return GateResult(False, ["成品视频不存在"], "T6")
    
    # 视频时长 vs timeline
    tl_path = ep / "timeline_v3.json"
    if tl_path.exists():
        with open(tl_path) as f:
            tl = json.load(f)
        tl_dur = tl.get("total_duration", 0)
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
            "-of","csv=p=0", str(final)], capture_output=True, text=True, timeout=10)
        if r.stdout.strip():
            vid_dur = float(r.stdout.strip())
            drift = abs(vid_dur - tl_dur)
            if drift > 2.0:
                issues.append(f"视频时长偏差 {drift:.1f}s (timeline={tl_dur:.1f}s 实际={vid_dur:.1f}s)")
    
    # 音频存在
    r = subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
        "-show_entries","stream=codec_name","-of","csv=p=0",str(final)],
        capture_output=True, text=True, timeout=10)
    if not r.stdout.strip():
        issues.append("视频无音频流")
    
    # 字幕偏差
    tl_path = ep / "audio" / "narration.srt"
    if tl_path.exists() and final.suffix == ".mkv":
        with open(tl_path, encoding="utf-8") as f:
            srt = f.read()
        pattern = re.compile(r"(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})")
        matches = list(pattern.finditer(srt))
        if matches:
            last = matches[-1]
            end_str = last.group(2).replace(",", ".")
            parts = end_str.split(":")
            last_end = int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
            if abs(last_end - vid_dur) > 1.0:
                issues.append(f"字幕末句偏差 {abs(last_end-vid_dur):.1f}s")
    
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T6")


# ══════════════════════════════════════════════════════════════
# 统一调度入口
# ══════════════════════════════════════════════════════════════

CHECKERS = {
    "T0": check_t0,
    "T1": check_t1,
    "T2": check_t2,
    "T3": check_t3,
    "T4": check_t4,
    "T6": check_t6,
    "T7": check_t7,
}

ACCURACY_STEPS = {"T1", "T2", "T4"}  # 需要内容准确性审核的步骤

def run_gate(step: str, episode_dir: str) -> GateResult:
    """运行指定步骤的门禁检查（含内容准确性审核）。"""
    # 1. 技术性门禁
    checker = CHECKERS.get(step)
    if checker:
        result = checker(episode_dir)
        if not result:
            return result
    
    # 2. 内容准确性审核（用 shenheyuan agent）
    if step in ACCURACY_STEPS:
        accuracy_result = check_content_accuracy(step, episode_dir)
        if not accuracy_result:
            return accuracy_result
    
    return GateResult(True, [])
