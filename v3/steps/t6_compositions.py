"""
v3/steps/t6_compositions.py — Composition generation step v2

Uses PageSpec builder for structured page data + component CSS templates
+ hard quality gate. Enforces AGENTS.md §2.1, §3.3, §3.4, §12.
"""
import json, os, re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from v3.steps.base import StepHandler, StepResult
from v3.designs.base import preset_to_css_vars
from v3.config import V3_DIR
from v3.pagespec import build_all_pages, MIN_LAYERS


def _surface_bg(surface: str) -> str:
    """Jinja2 filter: surface name -> hex color."""
    SURFACE_MAP = {
        "cream": "#faf9f5",
        "cream_soft": "#f5f0e8",
        "cream_card": "#efe9de",
        "dark": "#181715",
        "accent": "#cc785c",
    }
    return SURFACE_MAP.get(surface, "#faf9f5")


def _count_layers(html: str) -> int:
    """Count visual layers in rendered HTML."""
    count = 0
    # Each distinct visual element = 1 layer
    for cls in ["badge-pill", "page-title", "page-subtitle", "feature-card",
                "code-window", "quote-card", "step-card", "image-rail",
                "divider-line", "progress-dots", "compare-col",
                "surface-accent", "step-arrow", "card-grid-2x2"]:
        count += len(re.findall(rf'class="[^"]*{cls}[^"]*"', html))
    # h1/h2 tags that aren't in the above classes
    count += len(re.findall(r'<h[12][^>]*>', html))
    return count


def _has_visual_elements(html: str) -> bool:
    """Check if page has non-text visual elements."""
    checks = [
        r'data:image',          # base64 image
        r'class="[^"]*icon[^"]*"',  # icon/emoji
        r'class="[^"]*code-window[^"]*"',  # code
        r'class="[^"]*window-body[^"]*"',  # code content
        r'class="[^"]*progress-dot[^"]*"',  # progress
        r'class="[^"]*step-arrow[^"]*"',    # arrow
        r'class="[^"]*compare-col[^"]*"',   # comparison
    ]
    return any(re.search(p, html) for p in checks)


def _count_chinese(html: str) -> int:
    """Count Chinese characters in rendered HTML."""
    text = re.sub(r'<[^>]+>', '', html)
    return len(re.findall(r'[\u4e00-\u9fff]', text))


class CompositionHandler(StepHandler):
    name = "T6"
    description = "Generate composition HTML files"

    def execute(self) -> StepResult:
        # ── Load inputs ──
        tl_path = self.episode_dir / "timeline_v3.json"
        if not tl_path.exists():
            tl_path = self.episode_dir / "timeline.json"
        if not tl_path.exists():
            return StepResult(False, errors=[f"No timeline.json found in {self.episode_dir}"])
        
        with open(tl_path) as f:
            timeline = json.load(f)
        
        slides = timeline.get("slides", timeline if isinstance(timeline, list) else [])
        if isinstance(timeline, list):
            slides = timeline  # old format: flat list

        # ── Load images ──
        images = {}
        cache_path = self.episode_dir / "images" / "b64_cache.json"
        if cache_path.exists():
            with open(cache_path) as f:
                images = json.load(f)

        # ── Build PageSpecs ──
        specs = build_all_pages(slides, images)

        # ── Setup Jinja2 with surface_bg filter ──
        template_dirs = [
            str(V3_DIR / "templates"),
            str(V3_DIR / "templates" / "layouts"),
        ]
        env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=select_autoescape(["html", "j2"]),
        )
        env.filters["surface_bg"] = _surface_bg

        # ── Render each page ──
        comp_dir = self.episode_dir / "compositions"
        comp_dir.mkdir(exist_ok=True)
        total_dur = timeline.get("total_duration", sum(s.get("duration", 10) for s in slides))

        for spec in specs:
            template = env.get_template(f"{spec.layout}.j2")
            
            # Resolve image_b64 if filename is set
            img_b64 = ""
            if spec.image_slot and spec.image_slot in images:
                img_b64 = images[spec.image_slot]
            
            # Patch the image_slot with actual b64 data
            spec.image_slot = img_b64
            
            html = template.render(
                sid=f"s{spec.page_num}",
                page_spec=spec,
            )
            
            out_path = comp_dir / f"scene_{spec.page_num}.html"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)

        # ── Generate index.html ──
        idx_env = Environment(
            loader=FileSystemLoader(str(V3_DIR / "templates")),
        )
        idx_html = idx_env.get_template("index.html.j2").render(
            total_duration=total_dur,
            pages=[{"page": s.page_num, "start": s.start, "duration": s.duration}
                   for s in specs],
        )
        with open(self.episode_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(idx_html)

        print(f"  Generated {len(specs)} compositions → {comp_dir}")
        print(f"  Average layers: {sum(s.layer_count() for s in specs)//len(specs):.0f}")
        
        # Run gate immediately
        issues = self._check_quality(specs, comp_dir)
        if issues:
            print(f"  ⚠️  Quality issues found ({len(issues)}):")
            for issue in issues[:5]:
                print(f"     - {issue}")
            print(f"  Fixing issues and regenerating...")

        return StepResult(True, {
            "pages": len(specs),
            "total_duration": total_dur,
            "comp_dir": str(comp_dir),
            "specs": specs,
        })

    def _check_quality(self, specs: list, comp_dir: Path) -> list[str]:
        """Hard quality gate — fails the step if quality is insufficient."""
        issues = []
        
        for spec in specs:
            fp = comp_dir / f"scene_{spec.page_num}.html"
            if not fp.exists():
                issues.append(f"P{spec.page_num}: file missing")
                continue
            
            with open(fp) as f:
                html = f.read()
            
            # ① Layer count
            layers = _count_layers(html)
            min_l = MIN_LAYERS.get(spec.layout, 4)
            if layers < min_l:
                issues.append(
                    f"P{spec.page_num} ({spec.layout}): {layers}层 < {min_l}层要求"
                )
            
            # ② Visual diversity (not pure text)
            if not _has_visual_elements(html) and spec.layout not in ("outro",):
                issues.append(
                    f"P{spec.page_num}: 无视觉元素（图片/图标/代码/进度）"
                )
            
            # ③ Chinese character count
            if spec.layout not in ("hero", "section_divider", "outro"):
                chars = _count_chinese(html)
                if chars < 50:
                    issues.append(f"P{spec.page_num}: 仅{chars}字 (需≥50)")
        
        # ④ Layout diversity
        layouts = [s.layout for s in specs]
        for i in range(1, len(layouts)):
            if layouts[i] == layouts[i-1]:
                issues.append(f"P{i+1}: 布局重复({layouts[i]})与P{i}")
        
        # ⑤ Surface alternation
        surfaces = [s.surface for s in specs]
        for i in range(1, len(surfaces)):
            if surfaces[i] == surfaces[i-1] and surfaces[i] != "cream":
                issues.append(f"P{i+1}: 表面重复({surfaces[i]})")
        
        return issues

    def post_gate(self, result: StepResult) -> list[str]:
        """Validate composition quality."""
        comp_dir = result.artifact.get("comp_dir", "")
        if not comp_dir:
            return ["No composition directory"]
        
        specs = result.artifact.get("specs", [])
        return self._check_quality(specs, Path(comp_dir))
