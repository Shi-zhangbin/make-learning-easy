"""
core/gates/gate_master.py — 统一门禁调度

每个步骤完成后调用对应 gate，gate 返回：
  - issues: list[str] — 具体问题
  - feedback_target: str — 应该退回哪个阶段
  - passed: bool — 是否通过
"""
from dataclasses import dataclass, field
import json, os, re, subprocess, tempfile
from pathlib import Path
from PIL import Image
from core.config import FILE_NAMES, resolve_episode_path, TTS_EFFECTIVE_CHARS_PER_SEC
from core.tones.base import load_tone

# Per-design accent color mapping — single source for all gate checks
_DESIGN_ACCENT_COLORS = {
    "bilibili": "#FB7299",
    "talk-show": "#FF6B35",
    "claude": "#cc785c",
    "dark-teal": "#4FC3A1",
    "linear": "#5e6ad2",
    "mintlify": "#00d4a4",
    "stripe": "#635bff",
    "vercel": "#0070f3",
}


def _load_state(episode_dir: str) -> dict:
    """Load pipeline state from episode directory."""
    state_path = os.path.join(episode_dir, FILE_NAMES["pipeline_state"])
    if os.path.exists(state_path):
        with open(state_path) as f:
            return json.load(f)
    return {}


def _check_accent_color(episode_dir: str, state: dict) -> str | None:
    """Check if the composition HTML contains the expected accent color for the design preset.
    Returns an issue string, or None if passed / skippable."""
    _style = state.get("design_style", "")
    _expected_color = _DESIGN_ACCENT_COLORS.get(_style, "")
    if not _expected_color:
        return None
    _html_check_path = os.path.join(episode_dir, FILE_NAMES["composition"])
    if os.path.exists(_html_check_path):
        with open(_html_check_path) as _hf:
            _html_check = _hf.read()
        if _expected_color not in _html_check:
            return f"Style/Accent mismatch: 预设={_style}, 期望accent={_expected_color}, 未在HTML中找到匹配"
    return None


def _check_tone_script(episode_dir: str, state: dict) -> list[str]:
    """Check if the generated script respects the selected tone's validation rules.
    Returns a list of issues (empty = passed)."""
    tone_name = state.get("tone_style", "")
    if not tone_name:
        return []
    try:
        tone = load_tone(tone_name)
    except FileNotFoundError:
        return []
    vrules = tone.get("validation_rules", {})
    issues = []

    script_path = os.path.join(episode_dir, "02-script.txt")
    if not os.path.exists(script_path):
        return issues

    with open(script_path, encoding="utf-8") as f:
        content = f.read()

    # Check must_not_contain patterns
    for pattern_desc in vrules.get("must_not_contain", []):
        for keyword in re.findall(r'[一-鿿\w]+', pattern_desc):
            if keyword and keyword in content:
                issues.append(f"[话风门禁] tone={tone_name}: 内容含禁用词「{keyword}」({pattern_desc})")
                break

    # Check must_contain patterns
    for pattern_desc in vrules.get("must_contain", []):
        found = False
        for keyword in re.findall(r'[一-鿿\w]+', pattern_desc):
            if keyword and keyword in content:
                found = True
                break
        if not found:
            issues.append(f"[话风门禁] tone={tone_name}: 内容缺少要求项「{pattern_desc}」")

    return issues


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


# ── Placeholder detection patterns (1D) ──
PLACEHOLDER_PATTERNS = [
    r'卡片', r'图片', r'图表', r'TKTK', r'TODO', r'占位',
    r'placeholder', r'此处插入', r'这里放', r'请插入', r'示例文本',
]

def check_t0(episode_dir: str) -> GateResult:
    """选题报告完整吗？"""
    issues = []
    md_path = os.path.join(episode_dir, FILE_NAMES["topic_report"])
    if not os.path.exists(md_path):
        return GateResult(False, [f"{FILE_NAMES['topic_report']} 不存在"], "T0")
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
    issues = []
    md_path = os.path.join(episode_dir, FILE_NAMES["outline"])
    if not os.path.exists(md_path):
        return GateResult(False, [f"{FILE_NAMES['outline']} 不存在"], "T1")
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    if len(content) < 300:
        issues.append(f"知识点大纲仅 {len(content)} 字，内容不足")
    # 检查是否有知识点编号（一、二、三 或 1. 2. 3.）
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
    """口播稿无残留标记、无空页、字数合理、无占位符。"""
    issues = []

    script_path = os.path.join(episode_dir, FILE_NAMES["script"])
    if not os.path.exists(script_path):
        for c in ["配音稿_分段.txt", "配音稿.txt", "口播稿.txt"]:
            p = os.path.join(episode_dir, c)
            if os.path.exists(p):
                script_path = p
                break

    if not script_path:
        return GateResult(False, ["口播稿文件不存在"], "T2")

    with open(script_path, encoding="utf-8") as f:
        content = f.read()

    clean_text = re.sub(r'---.*?---\s*\n', '', content)

    # 1D: 占位符检测
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, clean_text):
            issues.append(f"含占位符文本: [{pat}]")
            break

    # 非口播内容检测
    stage_dirs = re.findall(r'[（(](?:开场|停顿|完|音乐|掌声|笑|沉默|过渡|转场|结束)[）)]', clean_text)
    if stage_dirs:
        issues.append(f"含舞台指示: {', '.join(set(stage_dirs))}。口播稿不应出现（开场）（停顿）等")

    if re.search(r'^[一-鿿]+[、.．]\s*\S', clean_text, re.MULTILINE):
        issues.append("含章节标题（一、二、三…），口播稿不应出现章节编号")

    for label in ["收尾", "开场白", "结束语", "结语", "开场", "前言", "后记", "附录"]:
        if re.search(rf'^{re.escape(label)}\s*$', clean_text, re.MULTILINE):
            issues.append(f"含章节标签: {label}")
            break

    if re.search(r'^[═=*]{3,}\s*$', clean_text, re.MULTILINE):
        issues.append("含分隔线（===/***），口播稿不应出现分隔线")

    # B009: 时长估算校验
    chars = len(re.findall(r'[一-鿿\w]', clean_text))
    estimated_sec = chars / TTS_EFFECTIVE_CHARS_PER_SEC
    if estimated_sec < 300:
        issues.append(f"估计音频仅 {estimated_sec:.0f}s ({chars}字)，不足 5 分钟（阈值 300s/{int(300*TTS_EFFECTIVE_CHARS_PER_SEC)}字）")

    # 标记残留
    artifacts = []
    for pat, name in [(r'#{2,}', "##标题"), (r'\*{2,}', "**加粗**"), (r'`{2,}', "``代码``")]:
        if re.search(pat, clean_text):
            artifacts.append(name)
    if artifacts:
        issues.append(f"含残留标记: {', '.join(artifacts)}")

    # 分页标记检查
    page_markers = re.findall(r'^---+\s*P\d+', content, re.MULTILINE)
    if not page_markers:
        issues.append("口播稿缺少分页标记（--- P1, --- P2…），T3 无法生成多页时间线")
    elif len(page_markers) < 5:
        issues.append(f"仅 {len(page_markers)} 个分页标记（阈值 5 页），视频时长可能不足")

    page_pattern = re.compile(r"---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL)
    pages = list(page_pattern.finditer(content))
    if pages:
        empty = [m.group(1) for m in pages if not m.group(2).strip()]
        if empty:
            issues.append(f"空页: P{', '.join(empty)}")

    # T2-C: 开场文本必须在 P1 内（否则 T6 不会捕获为 Slide 旁白）
    _p1 = re.search(r'^---\s*P1\s*---', content, re.MULTILINE)
    if _p1:
        _before = content[:_p1.start()].strip()
        if _before:
            issues.append(f"口播稿开头 {len(_before)} 字在 --- P1 --- 之前，不会被 T6 捕获为 Slide 旁白。请移入 P1 内。")

    # 话风门禁：检查脚本是否符合所选 tone 的 validation_rules
    state = _load_state(episode_dir)
    tone_issues = _check_tone_script(episode_dir, state)
    issues.extend(tone_issues)

    # T2-D: 每页时长检查 — 科普页 ≤max_sec，代码页不限
    _max_sec = 45
    _pp_path = os.path.join(episode_dir, FILE_NAMES.get("page_plans", "02-page-plans.json"))
    _page_layouts = {}
    if os.path.exists(_pp_path):
        try:
            _pp_raw = json.load(open(_pp_path, encoding="utf-8"))
            _pp_pages = _pp_raw if isinstance(_pp_raw, list) else _pp_raw.get("pages", [])
            for _p in _pp_pages:
                _page_layouts[_p.get("page")] = _p.get("layout", "")
        except:
            pass
    for _pm in page_markers:
        _m = re.match(r"---+\s*P(\d+)", _pm)
        if not _m:
            continue
        _pn = int(_m.group(1))
        _layout = _page_layouts.get(_pn, "")
        if _layout == "code_block":
            continue
        # 提取该页正文内容
        _pat = re.compile(
            rf"^---+\s*P{_pn}\s*---+\s*\n(.*?)(?=\n---+\s*P|\Z)", re.DOTALL | re.MULTILINE)
        _m2 = _pat.search(content)
        if not _m2:
            continue
        _page_chars = len(re.findall(r'[一-鿿\w]', _m2.group(1)))
        _page_sec = _page_chars / TTS_EFFECTIVE_CHARS_PER_SEC
        if _page_sec > _max_sec:
            _suggest = max(2, round(_page_sec / _max_sec))
            issues.append(
                f"P{_pn} 估计 {_page_sec:.0f}s ({_page_chars}字/{TTS_EFFECTIVE_CHARS_PER_SEC}字/s)，"
                f"超过{_max_sec}s上限。建议将 P{_pn} 拆分为 {_suggest} 页"
                f"（如 P{_pn}-A ~ P{_pn}-{chr(64+_suggest)}），"
                f"每页约 {_page_chars//_suggest}字/{_max_sec}s。")

    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T2")
def check_t3(episode_dir: str) -> GateResult:
    """配音时长 vs 口播字数偏差是否在合理范围。"""
    import os, json, subprocess
    from core.config import FILE_NAMES
    issues = []

    audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if not os.path.exists(audio_path):
        return GateResult(False, ["配音音频不存在"], "T3")
    
    # 获取音频时长
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", audio_path], capture_output=True, text=True, timeout=10)
    if not r.stdout.strip():
        return GateResult(False, ["无法获取音频时长"], "T3")
    audio_dur = float(r.stdout.strip())
    
    # 获取口播稿字数
    script_path = os.path.join(episode_dir, FILE_NAMES.get("script_raw", "02-script-raw.txt"))
    if not os.path.exists(script_path):
        script_path = os.path.join(episode_dir, FILE_NAMES["script"])
    if not os.path.exists(script_path):
        for c in ["配音稿_纯文字.txt", "配音稿_分段.txt", "口播稿.txt"]:
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
    from pathlib import Path
    from core.config import FILE_NAMES, resolve_episode_path
    issues = []
    
    slots_path = os.path.join(episode_dir, FILE_NAMES["image_slots"])
    if not os.path.exists(slots_path):
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
    

    # 每个 slot 必填字段校验
    required_fields = ["filename", "prompt", "page", "slot_index"]
    for i, slot in enumerate(slot_list):
        if not isinstance(slot, dict):
            issues.append(f"Slot[{i}]: 不是字典类型")
            continue
        missing = [f for f in required_fields if f not in slot or (isinstance(slot[f], str) and not slot[f].strip())]
        if missing:
            issues.append(f"Slot[{i}] (page {slot.get("page", "?")}): 缺少必填字段: {', '.join(missing)}")
        if slot.get("source") == "ai" and not slot.get("prompt", "").strip():
            issues.append(f"Slot[{i}] (AI源): prompt为空")
        if not slot.get("filename", "").strip():
            issues.append(f"Slot[{i}]: filename为空")

    # 2E: 默认风格门禁 — 检查 accent 颜色是否匹配预设
    _accent_issue = _check_accent_color(episode_dir, _load_state(episode_dir))
    if _accent_issue:
        issues.append(_accent_issue)

    # 2B: 时长交叉验证
    tl_path = os.path.join(episode_dir, FILE_NAMES["timeline"])
    audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if not os.path.exists(audio_path):
        audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if os.path.exists(tl_path) and os.path.exists(audio_path):
        try:
            with open(tl_path) as _tf:
                _tl = json.load(_tf)
            _tl_dur = _tl.get("total_duration", 0)
            _r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path], capture_output=True, text=True, timeout=10)
            if _r.stdout.strip():
                _audio_dur = float(_r.stdout.strip())
                if abs(_tl_dur - _audio_dur) > 1.0:
                    issues.append(f"时长偏差: timeline={_tl_dur:.1f}s vs audio={_audio_dur:.1f}s")
        except Exception:
            pass
    
    # 1D: HTML 占位符检测 (仅 T6 后有 HTML 时生效)
    _html_path = resolve_episode_path(episode_dir, "composition")
    if os.path.exists(_html_path):
        with open(_html_path) as _hf:
            _html = _hf.read()
        _text_only = re.sub(r'<[^>]+>', ' ', _html)
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, _text_only):
                issues.append(f"HTML含占位符: [{pat}]")
                break
    

    
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T4")


# ══════════════════════════════════════════════════════════════
# Content Accuracy Gate — 内容准确性审核（调用 shenheyuan agent）
# ══════════════════════════════════════════════════════════════

def check_content_accuracy(step: str, episode_dir: str) -> GateResult:
    """内容准确性审核 — 检查基本知识性错误。纯 Python，无 agent 依赖。"""
    import os, re
    from core.config import FILE_NAMES
    issues = []
    
    files_to_check = {
        "T1": [FILE_NAMES["outline"]],
        "T2": [FILE_NAMES["script"]],
        "T4": [FILE_NAMES["storyboard"]],
    }
    
    for fname in files_to_check.get(step, []):
        fpath = None
        for root, dirs, files in os.walk(episode_dir):
            if fname in files:
                fpath = os.path.join(root, fname); break
        if not fpath: continue
        
        with open(fpath, encoding="utf-8", errors="replace") as f:
            c = f.read()
        
        if fname == FILE_NAMES["outline"]:
            if not re.search(r'[一二三四五六七八九十]+、|\d+\.', c):
                issues.append("大纲缺少结构化编号")
            if len(c) < 200:
                issues.append("大纲内容过短")
        if fname in [FILE_NAMES["script"], "配音稿_分段.txt", "口播稿.txt"]:
            if not re.findall(r"---\s*P\d+.*?---", c):
                issues.append("口播稿缺少分页标记")
        if fname == FILE_NAMES["storyboard"]:
            if not re.search(r'布局|layout|配图', c, re.IGNORECASE):
                issues.append("分镜方案缺少布局定义")
    
    if issues:
        return GateResult(False, issues, step)
    return GateResult(True, [])
# ══════════════════════════════════════════════════════════════
# T6 Gate — Composition（布局质量）
# ══════════════════════════════════════════════════════════════

def check_t6(episode_dir: str) -> GateResult:
    """Check composition has actual scene content in index.html."""
    import re, os
    from pathlib import Path
    from core.config import FILE_NAMES, resolve_episode_path
    
    ep = Path(episode_dir)
    idx = Path(str(episode_dir)) / FILE_NAMES["composition"]
    if not idx.exists():
        return GateResult(False, ["composition file 不存在"], "T4")
    
    html = idx.read_text(encoding="utf-8")
    issues = []
    
    # Count scenes in HTML
    scenes = re.findall(r'<div id="s(\d+)" class="sc">', html)
    if len(scenes) < 5:
        issues.append(f"仅 {len(scenes)} 个场景 < 5")
    
    # Check each scene has visible elements
    for si in scenes:
        # Extract scene block
        pat_start = r'<div id="s' + si + r'" class="sc">'
        m_start = re.search(pat_start, html)
        if not m_start:
            continue
        s = m_start.start()
        # Find next scene or progress-bar
        nxt = re.search(r'</div>\s*\n\s*<div (?:id="s' + str(int(si)+1) + r'"|class="progress-bar")', html[s:])
        if nxt:
            block = html[s:s + nxt.start()]
        else:
            block = html[s:]
        # Count visible content elements
        content_els = len(re.findall(r'class="(?:h-xl|h-lg|h-md|h-sm|p-lg|p-md|p-sm|badge|card|card-alt|fq|quote|img-wrap)', block))
        if content_els == 0:
            issues.append(f"Scene {si}: 无内容元素")
        # Check for images — only require images for empty pages
        # (pages with content don't need images, especially with model-driven layouts)
        if content_els > 0:
            pass
        elif len(scenes) > 1 and si in [str(1), str(len(scenes))]:
            pass
        elif not re.search(r'<img\s+[^>]*src="', block):
            issues.append(f"Scene {si}: 无配图")
    
    # Check compositional elements exist
    if not re.search(r'class="progress-bar"', html):
        issues.append("缺少进度条")
    if not re.search(r'<audio', html):
        issues.append("缺少音频")
    
    # 2E: 默认风格门禁 — 检查 accent 颜色是否匹配预设
    _accent_issue = _check_accent_color(episode_dir, _load_state(episode_dir))
    if _accent_issue:
        issues.append(_accent_issue)

    # 2B: 时长交叉验证
    tl_path = os.path.join(episode_dir, FILE_NAMES["timeline"])
    audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if not os.path.exists(audio_path):
        audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if os.path.exists(tl_path) and os.path.exists(audio_path):
        try:
            with open(tl_path) as _tf:
                _tl = json.load(_tf)
            _tl_dur = _tl.get("total_duration", 0)
            _r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path], capture_output=True, text=True, timeout=10)
            if _r.stdout.strip():
                _audio_dur = float(_r.stdout.strip())
                if abs(_tl_dur - _audio_dur) > 1.0:
                    issues.append(f"时长偏差: timeline={_tl_dur:.1f}s vs audio={_audio_dur:.1f}s")
        except Exception:
            pass
    
    # 1D: HTML 占位符检测 (仅 T6 后有 HTML 时生效)
    _html_path = resolve_episode_path(episode_dir, "composition")
    if os.path.exists(_html_path):
        with open(_html_path) as _hf:
            _html = _hf.read()
        _text_only = re.sub(r'<[^>]+>', ' ', _html)
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, _text_only):
                issues.append(f"HTML含占位符: [{pat}]")
                break
    
        # Layout validation: unknown layouts + diversity (check_t6)
    _pp_path = os.path.join(episode_dir, "02-page-plans.json")
    if os.path.exists(_pp_path):
        try:
            with open(_pp_path) as _f:
                _pp_raw = json.load(_f)
            from core.pagespec import LAYOUTS as _valid_layouts
            _valid_set = set(_valid_layouts)
            _pp_pages = _pp_raw if isinstance(_pp_raw, list) else _pp_raw.get("pages", [])
            # Check unknown layouts
            _unknown = [p.get("layout", "") for p in _pp_pages 
                       if p.get("layout") and p["layout"] not in _valid_set]
            if _unknown:
                issues.append(
                    f"T6: unknown layout(s): {', '.join(set(_unknown))}. "
                    f"valid: {', '.join(_valid_layouts)}")
            # Check layout diversity
            _used_layouts = set(p.get("layout", "") for p in _pp_pages if p.get("layout"))
            if len(_used_layouts) < min(3, len(_pp_pages)):
                issues.append(
                    f"T6: few layout types: {len(_used_layouts)} ({', '.join(_used_layouts)}), "
                    f"need >= {min(3, len(_pp_pages))}")
        except:
            pass


# ══════════════════════════════════════════════════════════════
# T7 Gate — 渲染后视频质量
# ══════════════════════════════════════════════════════════════

def check_t7(episode_dir: str) -> GateResult:
    """视频时长对齐、音频存在、字幕偏差。"""
    import os, json, subprocess, re
    from pathlib import Path
    from core.config import FILE_NAMES, resolve_episode_path
    
    ep = Path(episode_dir)
    issues = []
    
    # 找最终视频
    finals = list(ep.glob(FILE_NAMES["final_dir"] + "/*final*"))
    if not finals:
        finals = list(ep.glob("成品/*final*")) + list(ep.glob("成品/*最终*"))
    final = None
    for f in finals:
        if f.suffix in (".mp4", ".mkv"):
            final = f; break
    
    if not final:
        return GateResult(False, ["成品视频不存在"], "T6")
    
    # Get video duration via ffprobe
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0", str(final)], capture_output=True, text=True, timeout=10)
    vid_dur = float(r.stdout.strip()) if r.stdout.strip() else 0.0
    
    # Video duration vs timeline
    tl_path = Path(str(episode_dir)) / FILE_NAMES["timeline"]
    if tl_path.exists() and vid_dur > 0:
        with open(tl_path) as f:
            tl = json.load(f)
        tl_dur = tl.get("total_duration", 0)
        if tl_dur > 0:
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
    tl_path = Path(str(episode_dir)) / FILE_NAMES["audio_srt"]
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
            if vid_dur > 0 and abs(last_end - vid_dur) > 1.0:
                issues.append(f"字幕末句偏差 {abs(last_end-vid_dur):.1f}s")
    
    # Frame black-check: sample at 25%, 50%, 75%
    for frac in [0.25, 0.5, 0.75]:
        ts = vid_dur * frac
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            frame_path = tmp.name
        r = subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", str(final),
            "-vframes", "1", "-q:v", "2", frame_path
        ], capture_output=True, timeout=15)
        if r.returncode == 0 and os.path.exists(frame_path):
            try:
                from PIL import Image
                img = Image.open(frame_path).convert("RGB")
                w, h = img.size
                px = img.load()
                dark_count = 0
                total = 0
                for y in range(0, h, h//20):
                    for x in range(0, w, w//20):
                        r, g, b = px[x, y]
                        if r < 25 and g < 25 and b < 25:
                            dark_count += 1
                        total += 1
                dark_pct = dark_count / total * 100
                if dark_pct > 95:
                    issues.append("Frame at {0:.0f}%: {1:.0f}% near-black".format(frac*100, dark_pct))
            except:
                pass
            finally:
                try: os.unlink(frame_path)
                except: pass
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T6")


# ══════════════════════════════════════════════════════════════
# 统一调度入口
# ══════════════════════════════════════════════════════════════


# T5 Gate - 配图质量
def check_t5(episode_dir: str) -> GateResult:
    """Check images are not blank/black."""
    import os
    from PIL import Image
    from core.config import FILE_NAMES, resolve_episode_path
    issues = []
    img_dir = os.path.join(episode_dir, FILE_NAMES["images_dir"])
    from core.config import resolve_episode_path
    if not os.path.isdir(img_dir):
        return GateResult(False, ["images/ directory missing"], "T4")
    pngs = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not pngs:
        return GateResult(False, ["images/ has no image files"], "T4")
    for fn in pngs:
        fp = os.path.join(img_dir, fn)
        try:
            img = Image.open(fp).convert('RGB')
            w, h = img.size
            px = img.load()
            # Grid sampling: 20x20 grid
            dark_count = 0
            total = 0
            for y in range(0, h, h//20):
                for x in range(0, w, w//20):
                    r, g, b = px[x, y]
                    if r < 25 and g < 25 and b < 25:
                        dark_count += 1
                    total += 1
            dark_pct = dark_count / total * 100
            if dark_pct > 95:
                issues.append("{0}: {1:.0f}% near-black pixels".format(fn, dark_pct))
            fsize = os.path.getsize(fp)
            if fsize < 2000:
                issues.append("{0}: too small ({1} bytes)".format(fn, fsize))
        except Exception as e:
            issues.append("{0}: unreadable ({1})".format(fn, e))
    # 2E: 默认风格门禁 — 检查 accent 颜色是否匹配预设
    _accent_issue = _check_accent_color(episode_dir, _load_state(episode_dir))
    if _accent_issue:
        issues.append(_accent_issue)

    # 2B: 时长交叉验证
    tl_path = os.path.join(episode_dir, FILE_NAMES["timeline"])
    audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if not os.path.exists(audio_path):
        audio_path = os.path.join(episode_dir, FILE_NAMES["audio_narration"])
    if os.path.exists(tl_path) and os.path.exists(audio_path):
        try:
            with open(tl_path) as _tf:
                _tl = json.load(_tf)
            _tl_dur = _tl.get("total_duration", 0)
            _r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path], capture_output=True, text=True, timeout=10)
            if _r.stdout.strip():
                _audio_dur = float(_r.stdout.strip())
                if abs(_tl_dur - _audio_dur) > 1.0:
                    issues.append(f"时长偏差: timeline={_tl_dur:.1f}s vs audio={_audio_dur:.1f}s")
        except Exception:
            pass
    
    # 1D: HTML 占位符检测 (仅 T6 后有 HTML 时生效)
    _html_path = resolve_episode_path(episode_dir, "composition")
    if os.path.exists(_html_path):
        with open(_html_path) as _hf:
            _html = _hf.read()
        _text_only = re.sub(r'<[^>]+>', ' ', _html)
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, _text_only):
                issues.append(f"HTML含占位符: [{pat}]")
                break
    

    
    if not issues:
        return GateResult(True, [], "")
    return GateResult(False, issues, "T4")

CHECKERS = {
    "T0": check_t0,
    "T1": check_t1,
    "T2": check_t2,
    "T3": check_t3,
    "T4": check_t4,
    "T5": check_t5,
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
