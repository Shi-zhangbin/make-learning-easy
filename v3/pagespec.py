"""
v3/pagespec.py — PageSpec data model + page builder

Every page in the video is described by a PageSpec object — structured data
that the templates render into visual components. This replaces the old
approach of passing raw narration strings to templates.
"""
from dataclasses import dataclass, field
from typing import Optional
import re, random


# ── Element-level models ──

@dataclass
class Card:
    """A single card within a section."""
    icon: str = ""           # emoji or empty
    title: str = ""
    body: str = ""
    style: str = "light"     # light / dark / accent / outline


@dataclass
class CodeBlock:
    """A code snippet within a section."""
    lines: list[str] = field(default_factory=list)
    language: str = "python"


@dataclass
class BulletList:
    """A bullet-point list."""
    items: list[str] = field(default_factory=list)


@dataclass
class ComparisonGroup:
    """Two-column comparison."""
    left_title: str = ""
    left_items: list[str] = field(default_factory=list)
    right_title: str = ""
    right_items: list[str] = field(default_factory=list)


# ── Section-level models ──

@dataclass
class Section:
    """A visual section/zone within a page."""
    style: str = "cream_soft"      # cream_soft / cream_card / dark / accent / divider
    cards: list[Card] = field(default_factory=list)
    code: Optional[CodeBlock] = None
    bullets: Optional[BulletList] = None
    comparison: Optional[ComparisonGroup] = None
    image_slot: str = ""
    image_position: str = "bottom"  # bottom / right / left / background            # which image slot to render here
    quote_text: str = ""
    quote_author: str = ""


# ── Step-level model ──

@dataclass
class FlowStep:
    """A step in a flowchart."""
    icon: str = ""
    title: str = ""
    body: str = ""


# ── Page-level model ──

LAYOUTS = [
    "hero", "concept", "flipped", "comparison",
    "code_block", "flowchart", "card_grid",
    "quote", "section_divider", "outro",
]

# Minimum visual layers per layout (AGENTS.md §2.1 + §12)
MIN_LAYERS = {
    "hero": 5,          # ①badge ②标题 ③副标题 ④进度 ⑤页码
    "concept": 6,       # ①badge ②h2 ③~3cards ④配图 ⑤section ⑥页码
    "flipped": 6,       # same as concept but image on left
    "comparison": 6,    # ①badge ②h2 ③左栏3层 ④右栏3层 ⑤分隔 ⑥页码
    "code_block": 5,    # ①badge ②h2 ③代码窗口 ④注解卡 ⑤页码
    "flowchart": 5,     # ①badge ②h2 ③~3步骤卡+箭头 ④类比说明 ⑤页码
    "card_grid": 5,     # ①badge ②h2 ③2×2网格 ④页码
    "quote": 4,         # ①标签 ②大字serif ③副标题 ④页码
    "section_divider": 4, # ①幕标 ②大标题 ③进度点 ④页码
    "outro": 3,         # ①标题 ②CTA ③装饰
}

# Surface alternation palette (Claude design system)
SURFACES = {
    "cream": "#faf9f5",
    "cream_soft": "#f5f0e8",
    "cream_card": "#efe9de",
    "dark": "#181715",
    "accent": "#cc785c",
}

# Emoji pool for auto-assignment
EMOJI_POOL = [
    "🧠", "⚡", "🔧", "📊", "🎯", "💡", "🔗", "🔄",
    "📦", "🏗️", "🔬", "🎨", "📈", "⚙️", "🔍", "🛠️",
]


@dataclass
class PageSpec:
    """Complete specification for one page/composition."""
    layout: str
    page_num: int
    total_pages: int
    duration: float
    start: float = 0.0
    
    # Visual
    surface: str = "cream"       # surface mode for page rhythm
    badge: str = ""
    title: str = ""
    subtitle: str = ""
    emoji: str = ""
    
    # Content sections (2-4 per page for density)
    sections: list[Section] = field(default_factory=list)
    
    # Flowchart-specific
    flow_steps: list[FlowStep] = field(default_factory=list)
    
    # Bottom zone
    image_slot: str = ""
    image_position: str = "bottom"  # bottom / right / left / background         # matched image filename
    
    def card_count(self) -> int:
        """Count total cards across all sections."""
        return sum(len(s.cards) for s in self.sections)
    
    @property
    def text_weight(self) -> float:
        """Adaptive flex weight for text area based on card count."""
        cards = self.card_count()
        if cards <= 1: return 1.0    # 50/50 split
        if cards <= 2: return 1.1    # 52/48
        if cards <= 3: return 1.2    # 55/45
        return 1.3                    # 57/43
    
    @property
    def image_weight(self) -> float:
        """Adaptive flex weight for image area. Inverse of text_weight."""
        return round(2.0 - self.text_weight, 1)
    
    @property
    def is_content_light(self) -> bool:
        """True when page has very little content (should center rather than stretch)."""
        return self.card_count() <= 1
    
    def layer_count(self) -> int:
        """Count visual layers in this page spec."""
        count = 0
        if self.badge: count += 1
        if self.title: count += 1
        if self.subtitle: count += 1
        count += len(self.sections)  # each section is a visual zone
        for s in self.sections:
            count += len(s.cards)
            if s.code: count += 1
            if s.bullets: count += 1
            if s.comparison: count += 1
            if s.quote_text: count += 1
        if self.image_slot: count += 1
        count += 1  # page number
        if self.emoji: count += 1
        return count


# ══════════════════════════════════════════════════════════════════
# PageSpec Builder
# ══════════════════════════════════════════════════════════════════

SURFACE_ORDER = ["cream", "cream_soft", "cream_card", "cream_soft"]
# Dark surfaces only for specific layouts
DARK_LAYOUTS = {"code_block", "quote"}
BADGE_PREFIXES = {
    "hero": "开场", "concept": "核心概念", "flipped": "深入理解",
    "comparison": "对比", "code_block": "代码实践",
    "flowchart": "流程", "card_grid": "要点归纳",
    "quote": "引述", "section_divider": "章节", "outro": "总结",
}


def _auto_emoji(title: str, fallback: str = "💡") -> str:
    """Pick an emoji based on title keywords."""
    kw_map = {
        "概念": "🧠", "原理": "🔬", "对比": "⚖️", "结构": "🏗️",
        "流程": "🔄", "代码": "💻", "数据": "📊", "总结": "🎯",
        "注意": "⚠️", "类比": "🎨", "核心": "💡", "关键": "🔑",
        "问题": "❓", "答案": "✅", "算法": "⚙️", "网络": "🔗",
        "函数": "📐", "模型": "📦", "训练": "🏋️", "推理": "🔍",
    }
    for kw, emoji in kw_map.items():
        if kw in title:
            return emoji
    return random.choice(EMOJI_POOL)


def _smart_truncate(text: str, max_len: int = 120) -> str:
    """Truncate at sentence boundary."""
    if len(text) <= max_len:
        return text
    # Find last sentence end within limit
    cut = text[:max_len]
    last_end = max(cut.rfind("。"), cut.rfind("！"), cut.rfind("？"))
    if last_end > 0:
        return cut[:last_end + 1]
    return cut + "…"


def build_pagespec(
    layout: str,
    page_num: int,
    total_pages: int,
    duration: float,
    start: float,
    title: str,
    narration: str,
    code_text: str = "",
    image_filename: str = "",
    prev_surface: str = "",
) -> PageSpec:
    """
    Transform raw content into a structured PageSpec.
    
    This is the key function that enforces quality:
    - Picks appropriate icons
    - Creates right number of sections/cards for layout type
    - Ensures minimum layer count
    - Alternates surface rhythm
    """
    
    # ── Surface alternation ──
    # All pages in cream family: cream → cream_soft → cream_card → cream_soft → ...
    layout_to_start = {"hero": "cream", "code_block": "cream_soft", "quote": "cream_card"}
    if not prev_surface or prev_surface == "dark":
        surface = layout_to_start.get(layout, "cream")
    else:
        idx = SURFACE_ORDER.index(prev_surface) if prev_surface in SURFACE_ORDER else 0
        surface = SURFACE_ORDER[(idx + 1) % len(SURFACE_ORDER)]
    
    # ── Badge ──
    badge_prefix = BADGE_PREFIXES.get(layout, "章节")
    badge = f"{badge_prefix} {page_num}"
    
    # ── Emoji ──
    emoji = _auto_emoji(title)
    
    # ── Parse narration into sentences ──
    clean = narration.replace("\\n", "\n").strip()
    sentences = [s.strip() for s in re.split(r'[。！？\n]', clean) if len(s.strip()) > 5]
    
    # ── Subtitle = first sentence ──
    subtitle = _smart_truncate(sentences[0], 80) if sentences else ""
    
    # ── Sections ──
    sections = []
    
    if layout in ("hero", "section_divider", "outro"):
        # Hero / Divider / Outro: minimal cards, focus on title
        if sentences[1:]:
            s = Section(
                style="cream_card" if layout != "outro" else "cream_soft",
                cards=[Card(
                    icon=_auto_emoji(s),
                    body=_smart_truncate(s, 100),
                ) for s in sentences[1:4]],
            )
            sections.append(s)
    
    elif layout in ("concept", "flipped"):
        # Concept: 2-3 feature cards + optional code
        cards = []
        for s in sentences[1:5]:
            # First 20 chars as pseudo-title
            pseudo_title = s[:15] + ("…" if len(s) > 15 else "")
            cards.append(Card(
                icon=_auto_emoji(pseudo_title),
                title=pseudo_title,
                body=_smart_truncate(s, 120),
            ))
        if cards:
            sections.append(Section(style="cream_card", cards=cards[:3]))
        
        # Add code section if available
        if code_text:
            sections.append(Section(
                style="dark",
                code=CodeBlock(lines=code_text.split("\n")[:8]),
            ))
        
        # If still thin, add a key point
        if len(sections) < 2 and len(sentences) > 5:
            sections.append(Section(
                style="accent",
                cards=[Card(body=_smart_truncate(sentences[-1], 80))],
            ))
    
    elif layout == "comparison":
        # Comparison: split narration into left/right
        mid = len(sentences) // 2
        left = sentences[1:mid+1]
        right = sentences[mid+1:5]
        sections.append(Section(
            style="cream_card",
            comparison=ComparisonGroup(
                left_title="方案一",
                left_items=left[:3],
                right_title="方案二",
                right_items=right[:3],
            )
        ))
    
    elif layout == "code_block":
        # Code block: code window + annotation cards
        if code_text:
            sections.append(Section(
                style="dark",
                code=CodeBlock(lines=code_text.split("\n")[:12]),
            ))
        annotations = [s for s in sentences[1:4] if len(s) > 10]
        if annotations:
            sections.append(Section(
                style="cream_card",
                cards=[Card(body=_smart_truncate(s, 100)) for s in annotations],
            ))
    
    elif layout == "flowchart":
        # Flowchart: 3-5 steps
        steps = sentences[1:6]
        if steps:
            sections.append(Section(
                style="cream_card",
                cards=[Card(
                    icon=_auto_emoji(s),
                    body=_smart_truncate(s, 60),
                ) for s in steps[:4]],
            ))
    
    elif layout == "card_grid":
        # Card grid: 2x2
        items = sentences[1:5]
        while len(items) < 4:
            items.append("")
        sections.append(Section(
            style="cream_card",
            cards=[Card(
                icon=_auto_emoji(s),
                body=_smart_truncate(s, 80),
            ) for s in items[:4] if s],
        ))
    
    elif layout == "quote":
        # Quote: dark background, centered
        quote = sentences[1] if len(sentences) > 1 else title
        author = sentences[0] if sentences else ""
        sections.append(Section(
            style="dark",
            quote_text=quote,
            quote_author=author,
        ))
    
    # ── Thickness enforcement: ensure minimum layers for thin pages ──
    temp = PageSpec(
        layout=layout, page_num=page_num, total_pages=total_pages,
        duration=duration, start=start, surface=surface,
        badge=badge, title=title, subtitle=subtitle,
        emoji=emoji, sections=sections, image_slot=image_filename,
    )
    
    if temp.layer_count() < MIN_LAYERS.get(layout, 4):
        # Pad thin pages with decorative/structural sections
        deficit = MIN_LAYERS.get(layout, 4) - temp.layer_count()
        for _ in range(deficit):
            if layout == "quote":
                # Add quote_text from title if missing
                if not any(s.quote_text for s in sections):
                    sections.append(Section(
                        style="dark",
                        quote_text=title,
                        quote_author=subtitle or "关键要点",
                    ))
            elif not any(s.code for s in sections):
                # Add a decorative divider or card
                sections.append(Section(
                    style="cream_soft" if surface != "cream_soft" else "cream_card",
                    cards=[Card(body=subtitle or title)],
                ))
    
    # Choose image position based on layout
    img_pos = "right" if layout in ("concept",) else "left" if layout in ("flipped",) else "bottom"
    
    return PageSpec(
        layout=layout, page_num=page_num, total_pages=total_pages,
        duration=duration, start=start, surface=surface,
        badge=badge, title=title, subtitle=subtitle,
        emoji=emoji, sections=sections, image_slot=image_filename,
        image_position=img_pos,
    )


def _auto_select_layouts(slides: list[dict]) -> list[str]:
    """Analyze narration content and select best layout for each slide."""
    total = len(slides)
    layouts = []
    
    # Keyword → layout mapping
    layout_keywords = {
        "code_block": ["代码", "实现", "import", "def ", "class ",
                       "编程", "程序", "API"],
        "comparison": ["对比", "区别", "差异", "vs", "不同点", "优缺点",
                       "相比之下", "另一方面"],
        "flowchart":  ["步骤", "流程", "第一阶段", "第一步", "第1步", "第2步",
                       "步骤1", "步骤2", "步骤3"],
        "quote":      ["引述", "名言", "说过", "曾言", "总结道"],
        "section_divider": ["章节", "告一段落", "接下来我们"],
    }
    
    for i, slide in enumerate(slides):
        # First slide is always hero
        if i == 0:
            layouts.append("hero")
            continue
        
        # Last slide is always outro
        if i == total - 1:
            layouts.append("outro")
            continue
        
        narration = slide.get("narration", slide.get("narration_text", ""))
        title = slide.get("title", slide.get("label", ""))
        code_text = slide.get("code", "")
        text = (title + " " + narration).lower()
        
        # If slide has explicit code content, use code_block
        if code_text or "代码" in text:
            layouts.append("code_block")
            continue
        
        # Score each layout type by keyword matches
        scores = {}
        for layout, keywords in layout_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scores[layout] = score
        
        best = max(scores, key=scores.get) if scores else None
        
        # Use best match, or fallback rotation
        if best:
            candidate = best
        else:
            # Fallback rotation through concept variants
            fallbacks = ["concept", "flipped", "card_grid", "concept"]
            candidate = fallbacks[(i - 1) % len(fallbacks)]
        
        # Ensure no consecutive repeats
        if layouts and candidate == layouts[-1]:
            alternatives = [l for l in ["concept", "card_grid", "comparison", "flowchart"]
                          if l != candidate]
            if alternatives:
                candidate = alternatives[(i) % len(alternatives)]
        
        # Short narration → section_divider or card_grid
        if len(narration) < 30 and candidate not in ("code_block", "quote"):
            if "章节" in text or candidate == "concept":
                candidate = "section_divider" if i % 3 == 1 else "card_grid"
        
        layouts.append(candidate)
    
    return layouts


def build_all_pages(
    slides: list[dict],
    images: dict[str, str],
    layout_rotation: list[str] | None = None,
) -> list[PageSpec]:
    """Build PageSpecs for all slides in a timeline."""
    total = len(slides)
    specs = []
    prev_surface = ""
    
    # Auto-select layout based on content analysis
    if layout_rotation is None:
        layout_rotation = _auto_select_layouts(slides)
    
    for i, slide in enumerate(slides):
        pg = i + 1
        layout = layout_rotation[i] if i < len(layout_rotation) else "concept"
        
        title = slide.get("title", slide.get("label", f"P{pg}"))
        narration = slide.get("narration", slide.get("narration_text", ""))
        code = slide.get("code", "")
        
        # Match image
        img_fn = ""
        for fn in images:
            if f"p{pg:02d}" in fn.lower() or f"P{pg:02d}" in fn or str(pg) in fn:
                img_fn = fn
                break
        
        spec = build_pagespec(
            layout=layout,
            page_num=pg,
            total_pages=total,
            duration=slide.get("duration", 10),
            start=slide.get("start", 0),
            title=title,
            narration=narration,
            code_text=code,
            image_filename=img_fn,
            prev_surface=prev_surface,
        )
        
        prev_surface = spec.surface
        specs.append(spec)
    
    return specs
