"""
v3/steps/t6_compositions.py — Element-driven HyperFrames engine

No fixed layouts. Each scene is an array of elements.
Each element type maps to a renderer + GSAP entrance animation.
All in one HyperFrames composition with push transitions + ambient.
"""
import json, os
from pathlib import Path
from v3.steps.base import StepHandler, StepResult
from v3.designs.base import load_preset


def _load_design(episode_dir):
    state_path = os.path.join(episode_dir, "pipeline_state.json")
    style = "claude"
    if os.path.exists(state_path):
        with open(state_path) as f:
            s = json.load(f)
        style = s.get("design_style", "claude")
    try:
        return load_preset(style)
    except FileNotFoundError:
        return load_preset("claude")


def _render(design, slides, audio_path="", html_path=""):
    """Element-driven HyperFrames composition generator."""
    ld = design.get("layout_defaults", {})
    c = design.get("colors", {})
    bg = ld.get("canvas_bg", "#faf9f5")
    heading_fam = ld.get("heading_family", "sans-serif")
    body_fam = ld.get("body_family", "sans-serif")
    n = len(slides)
    total_dur = sum(s.get("duration", 8) for s in slides)
    trans = 0.45

    # Google Fonts
    hf = heading_fam.replace('"', '').replace("'", "")
    bf = body_fam.replace('"', '').replace("'", "")
    gf_url = ""
    for name in [hf, bf]:
        simple = name.split(",")[0].strip()
        if simple and simple not in ("sans-serif", "serif", "monospace"):
            pn = simple.replace(" ", "+")
            gf_url = f'https://fonts.googleapis.com/css2?family={pn}:wght@300;400;500;600;700&display=swap'

    # CSS
    scene_css = "\n".join(
        f'    #s{i+1} {{ z-index: {i+1}; background: {bg}; opacity: {"1" if i == 0 else "0"}; }}'
        for i in range(n))

    css_vars = f"""
    :root {{
    --canvas: {ld.get('canvas_bg', c.get('canvas', '#faf9f5'))};
    --card: {ld.get('card_bg', c.get('surface_card', '#ffffff'))};
    --border: {ld.get('border_color', c.get('hairline', '#e2e4e8'))};
    --ink: {ld.get('heading_color', c.get('ink', '#1a1a2e'))};
    --body: {ld.get('body_color', c.get('body', '#3d3d4a'))};
    --muted: {ld.get('muted_color', c.get('muted', '#7a7a8a'))};
    --accent: {ld.get('accent_color', c.get('primary', '#3a5a9f'))};
    --code-bg: {ld.get('code_bg', c.get('code_bg', '#0d0d14'))};
    --code-fg: {ld.get('code_fg', c.get('code_text', '#c0caf5'))};
    --hf: {heading_fam};
    --bf: {body_fam};
    --cf: {ld.get('code_family', 'monospace')};
    }}
"""

    common_css = f"""
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html,body {{ margin:0; width:1920px; height:1080px; overflow:hidden; background:{bg}; }}
    body {{ font-family:var(--bf); }}
    .dsp {{ font-family:var(--hf); }}

    .sc {{ display:flex; position:absolute; top:0; left:0; width:1920px; height:1080px; }}
    .sci {{ display:flex; flex-direction:column; width:100%; height:100%; padding:100px 140px; gap:14px; box-sizing:border-box; position:relative; }}

    .badge {{ display:inline-block; align-self:flex-start; background:color-mix(in srgb,var(--accent)12%,transparent); color:var(--accent); border-radius:6px; padding:3px 14px; font-size:13px; font-weight:600; letter-spacing:0.3px; }}
    .h-xl {{ font-size:90px; font-weight:700; color:var(--ink); line-height:1.05; }}
    .h-lg {{ font-size:56px; font-weight:700; color:var(--ink); line-height:1.1; }}
    .h-md {{ font-size:42px; font-weight:700; color:var(--ink); line-height:1.15; }}
    .h-sm {{ font-size:32px; font-weight:600; color:var(--ink); line-height:1.2; }}
    .p-lg {{ font-size:22px; font-weight:400; color:var(--muted); line-height:1.5; max-width:70%; }}
    .p-md {{ font-size:17px; font-weight:400; color:var(--body); line-height:1.55; }}
    .p-sm {{ font-size:14px; font-weight:400; color:var(--muted); line-height:1.5; }}
    .accent-line {{ width:60px; height:3px; background:var(--accent); border-radius:2px; }}

    .card-row {{ display:flex; gap:18px; flex-shrink:0; }}
    .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:20px 24px; flex:1; display:flex; flex-direction:column; gap:6px; }}
    .card .ci {{ font-size:26px; }}
    .card .ct {{ font-family:var(--hf); font-size:20px; font-weight:600; color:var(--ink); }}
    .card .cb {{ font-size:15px; color:var(--body); line-height:1.5; }}

    .card-alt {{ border-left:3px solid var(--accent); border-radius:12px; background:var(--card); padding:18px 22px; display:flex; align-items:center; gap:16px; }}
    .card-alt .ci {{ font-size:24px; flex-shrink:0; }}
    .card-alt .ca-name {{ font-family:var(--hf); font-size:22px; font-weight:600; color:var(--ink); }}
    .card-alt .ca-desc {{ font-size:14px; color:var(--body); line-height:1.4; }}
    .card-alt .ca-tag {{ font-family:var(--cf); font-size:12px; font-weight:500; color:var(--accent); margin-left:auto; }}

    .grid-2x2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; flex-shrink:0; }}

    .split {{ display:flex; flex-direction:row; gap:24px; flex:1; min-height:0; }}
    .split-l,.split-r {{ display:flex; flex-direction:column; gap:14px; }}
    .split-l {{ flex:1.2; }}
    .split-r {{ flex:1; }}

    .img-wrap {{ display:flex; align-items:center; justify-content:center; overflow:hidden; border-radius:12px; background:color-mix(in srgb,var(--canvas)60%,black); border:1px solid var(--border); }}
    .img-wrap img {{ width:100%; height:100%; object-fit:contain; padding:4px; }}

    .code-w {{ background:var(--code-bg); border-radius:12px; overflow:hidden; display:flex; flex-direction:column; }}
    .code-w .ch {{ background:#16161e; height:32px; display:flex; align-items:center; padding:0 14px; gap:6px; flex-shrink:0; }}
    .code-w .cd {{ width:10px; height:10px; border-radius:50%; }}
    .code-w .cb {{ padding:16px 20px; font-family:var(--cf); font-size:14px; line-height:1.65; color:var(--code-fg); white-space:pre-wrap; flex:1; overflow-y:auto; }}

    .chip-row {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .chip {{ font-size:12px; font-weight:500; color:var(--accent); letter-spacing:0.1em; text-transform:uppercase; padding:5px 14px; border:1px solid color-mix(in srgb,var(--accent)25%,transparent); border-radius:20px; }}

    .fq-grid {{ display:flex; flex-direction:column; gap:18px; }}
    .fq {{ display:flex; align-items:flex-start; gap:16px; }}
    .fq-n {{ font-family:var(--hf); font-size:38px; font-weight:700; color:color-mix(in srgb,var(--accent)25%,transparent); line-height:1; width:40px; flex-shrink:0; }}
    .fq-q {{ font-size:22px; font-weight:600; color:var(--ink); line-height:1.3; }}
    .fq-a {{ font-size:15px; font-weight:400; color:var(--body); line-height:1.5; }}

    .quote {{ background:var(--code-bg); border-radius:12px; padding:48px 60px; text-align:center; }}
    .quote .qt {{ font-size:32px; font-weight:400; line-height:1.4; color:#e0e0e0; }}
    .quote .qa {{ font-size:16px; color:var(--accent); margin-top:12px; }}

    .spacer {{ height:16px; }}
    .spacer-lg {{ height:32px; }}
    .pn {{ position:absolute; bottom:28px; right:40px; font-size:14px; font-weight:500; color:color-mix(in srgb,var(--ink)15%,transparent); }}

    .progress-bar {{ position:absolute; bottom:0; left:0; right:0; height:52px; background:linear-gradient(to top,var(--card),transparent); display:flex; align-items:flex-end; padding:0 140px 10px; gap:10px; z-index:999; pointer-events:none; }}
    .progress-track {{ flex:1; height:3px; position:relative; }}
    .progress-bg {{ height:100%; background:color-mix(in srgb,var(--accent)20%,transparent); border-radius:2px; width:100%; overflow:hidden; }}
    .progress-fill {{ height:3px; background:var(--accent); border-radius:2px; width:0%; position:relative; }}
    .progress-label {{ font-size:12px; font-weight:500; color:var(--muted); white-space:nowrap; min-width:30px; text-align:right; font-feature-settings:'tnum'; }}
    .dancer {{ position:absolute; bottom:-6px; left:0%; width:60px; height:60px; transform-origin:center bottom; background-image:url("sprite_sheet.png"); background-size:540px 60px; image-rendering:auto; animation:spriteRun 1s steps(9) infinite; z-index:1000; }}
    @keyframes spriteRun {{
  0% {{ background-position: 0px 0px; }}
  100% {{ background-position: -540px 0px; }}
}}

    .bg-glow {{ position:absolute; border-radius:50%; pointer-events:none; }}
    .bg-glow-1 {{ width:800px; height:800px; background:radial-gradient(circle,var(--accent)08 0%,transparent 70%); top:50%; left:50%; transform:translate(-50%,-50%); }}
"""

    # Build per-element renderers
    def render_elem(el, pg):
        t = el.get("type", "")
        if t == "badge":
            return f'<div class="badge">{el.get("text","")}</div>'
        elif t == "heading":
            sz = el.get("size", "lg")
            cls = {"xl": "h-xl dsp", "lg": "h-lg dsp", "md": "h-md dsp", "sm": "h-sm dsp"}.get(sz, "h-lg dsp")
            return f'<h1 class="{cls}">{el.get("text","")}</h1>'
        elif t == "paragraph":
            sz = el.get("size", "md")
            cls = {"lg": "p-lg", "md": "p-md", "sm": "p-sm"}.get(sz, "p-md")
            return f'<p class="{cls}">{el.get("text","")}</p>'
        elif t == "accent-line":
            return '<div class="accent-line"></div>'
        elif t == "spacer":
            sz = "spacer-lg" if el.get("size") == "lg" else "spacer"
            return f'<div class="{sz}"></div>'
        elif t == "chip-row":
            chips = "".join(f'<span class="chip">{ch}</span>' for ch in el.get("chips", []))
            return f'<div class="chip-row">{chips}</div>'
        elif t == "card-row":
            cards = ""
            for c in el.get("cards", []):
                icon = f'<div class="ci">{c.get("icon","")}</div>' if c.get("icon") else ""
                title = f'<div class="ct">{c.get("title","")}</div>' if c.get("title") else ""
                body = f'<div class="cb">{c.get("body","")}</div>' if c.get("body") else ""
                cards += f'<div class="card">{icon}{title}{body}</div>'
            return f'<div class="card-row">{cards}</div>'
        elif t == "card-alt":
            icon = f'<div class="ci">{el.get("icon","")}</div>' if el.get("icon") else ""
            tag = f'<div class="ca-tag">{el.get("tag","")}</div>' if el.get("tag") else ""
            title = f'<div class="ca-name">{el.get("title","")}</div>' if el.get("title") else ""
            desc = f'<div class="ca-desc">{el.get("desc","")}</div>' if el.get("desc") else ""
            return f'<div class="card-alt">{icon}<div style="flex:1">{title}{desc}</div>{tag}</div>'
        elif t == "card-alt-row":
            items = ""
            for c in el.get("cards", []):
                icon = f'<div class="ci">{c.get("icon","")}</div>' if c.get("icon") else ""
                tag = f'<div class="ca-tag">{c.get("tag","")}</div>' if c.get("tag") else ""
                items += f'<div class="card-alt">{icon}<div style="flex:1"><div class="ca-name">{c.get("title","")}</div><div class="ca-desc">{c.get("desc","")}</div></div>{tag}</div>'
            return f'<div style="display:flex;flex-direction:column;gap:12px;">{items}</div>'
        elif t == "grid-2x2":
            cards = ""
            for c in el.get("cards", []):
                icon = f'<div style="font-size:24px">{c.get("icon","")}</div>' if c.get("icon") else ""
                title = f'<div class="ct">{c.get("title","")}</div>' if c.get("title") else ""
                body = f'<div class="cb">{c.get("body","")}</div>' if c.get("body") else ""
                cards += f'<div class="card">{icon}{title}{body}</div>'
            return f'<div class="grid-2x2">{cards}</div>'
        elif t == "image":
            sz = el.get("size", "medium")
            height = {"small": "120px", "medium": "240px", "large": "400px", "fill": "1"}.get(sz, "240px")
            if sz == "fill":
                return f'<div class="img-wrap" style="flex:1;min-height:100px;"><img src="{el.get("src","")}" alt=""></div>'
            return f'<div class="img-wrap" style="flex-shrink:0;height:{height};"><img src="{el.get("src","")}" alt=""></div>'
        elif t == "code":
            lines = el.get("code", el.get("text", ""))
            return f'<div class="code-w" style="flex:1"><div class="ch"><span class="cd" style="background:#ff5f56;"></span><span class="cd" style="background:#ffbd2e;"></span><span class="cd" style="background:#27c93f;"></span><span style="margin-left:10px;font-family:monospace;font-size:12px;color:#888;">{el.get("lang","")}</span></div><div class="cb">{lines}</div></div>'
        elif t == "split":
            left = ""
            for sub in el.get("left", []):
                left += render_elem(sub, pg)
            right = ""
            for sub in el.get("right", []):
                right += render_elem(sub, pg)
            lw = el.get("left_weight", 1.2)
            rw = el.get("right_weight", 1)
            return f'<div class="split"><div class="split-l" style="flex:{lw}">{left}</div><div class="split-r" style="flex:{rw}">{right}</div></div>'
        elif t == "fq-row":
            rows = ""
            for i, r in enumerate(el.get("rows", [])):
                rows += f'<div class="fq"><div class="fq-n">{i+1:02d}</div><div><div class="fq-q">{r.get("q","")}</div><div class="fq-a">{r.get("a","")}</div></div></div>'
            return f'<div class="fq-grid">{rows}</div>'
        elif t == "quote":
            return f'<div class="quote"><div class="qt">{el.get("text","")}</div>{f"<div class=\"qa\">{el.get('author','')}</div>" if el.get("author") else ""}</div>'
        elif t == "button":
            return f'<div style="display:flex;justify-content:center;margin-top:8px;"><div class="badge" style="border:2px solid var(--accent);background:transparent;padding:8px 28px;border-radius:999px;cursor:default;">{el.get("text","")}</div></div>'
        return ""

    # Scene entrance animation map per element type
    def entrance_for(elem, pg, t, idx):
        etype = elem.get("type", "")
        delay = t + 0.15 + idx * 0.08
        mapping = {
            "badge": f'y:12,opacity:0,duration:0.3',
            "heading": f'y:25,opacity:0,duration:0.5',
            "paragraph": f'y:15,opacity:0,duration:0.4',
            "accent-line": f'scaleX:0,opacity:0,duration:0.4',
            "spacer": f'opacity:0,duration:0.01',
            "chip-row": f'y:12,opacity:0,duration:0.3',
            "card-row": f'y:20,opacity:0,duration:0.45',
            "card-alt": f'x:-15,opacity:0,duration:0.4',
            "card-alt-row": f'y:15,opacity:0,duration:0.4',
            "grid-2x2": f'y:15,opacity:0,duration:0.4',
            "image": f'scale:0.95,opacity:0,duration:0.5',
            "code": f'x:-15,opacity:0,duration:0.5',
            "split": f'opacity:0,duration:0.4',
            "fq-row": f'y:15,opacity:0,duration:0.4',
            "quote": f'y:15,opacity:0,duration:0.5',
            "button": f'scale:0.9,opacity:0,duration:0.4',
        }
        props = mapping.get(etype)
        if not props:
            return ""
        ease = "power2.out" if etype in ("badge", "paragraph", "chip-row", "card-alt", "fq-row") else "power3.out" if etype in ("card-row", "grid-2x2") else "expo.out" if etype in ("heading",) else "power2.out"
        if etype == "card-row":
            return f'    tl.from("#s{pg} .card", {{ y:20, opacity:0, duration:0.4, ease:"power3.out", stagger:0.08 }}, {delay});\n'
        if etype == "card-alt-row":
            return f'    tl.from("#s{pg} .card-alt:nth-child({idx+1})", {{ x:-15, opacity:0, duration:0.4, ease:"power3.out" }}, {delay});\n'
        sel = f"#s{pg} > .sci > :nth-child({idx+1})"
        return f'    tl.from("{sel}", {{ {props}, ease:"{ease}" }}, {delay});\n'

    # Build all scenes
    all_scenes = ""
    all_js = ""
    t = 0.0

    for i, slide in enumerate(slides):
        pg = i + 1
        dur = slide.get("duration", 8)
        elements = slide.get("elements", slide.get("slides", []))

        inner = ""
        js = f"\n    // Scene {pg}\n"
        visible_el_idx = 0

        for idx, el in enumerate(elements):
            html = render_elem(el, pg)
            if html:
                inner += f"      {html}\n"
                js += entrance_for(el, pg, t, visible_el_idx)
                visible_el_idx += 1

        all_scenes += f"""
  <div id="s{pg}" class="sc">
    <div class="sci">
      {inner}
      <div style="display:none;"></div>
    </div>
  </div>"""
        all_js += js

        if i < n - 1:
            nt = t + dur
            all_js += f"""    tl.to("#s{pg}", {{ y:-1080, duration:{trans}, ease:"power3.inOut" }}, {nt});
    tl.fromTo("#s{pg+1}", {{ y:1080, opacity:0 }}, {{ y:0, opacity:1, duration:{trans}, ease:"power3.inOut" }}, {nt});
    tl.set("#s{pg}", {{ visibility:"hidden" }}, {nt + trans + 0.1});
    tl.set("#pl", {{ innerText:'{pg+1}/{n}' }}, {nt});
"""
        else:
            fe = t + dur - 2
            all_js += f"""    tl.to("#s{pg} .h-xl,#s{pg} .h-lg,#s{pg} .h-md", {{ y:-25, opacity:0, duration:0.4, ease:"power2.in" }}, {fe});
    tl.to("#s{pg} .p-lg,#s{pg} .p-md", {{ y:-15, opacity:0, duration:0.3, ease:"power2.in" }}, {fe + 0.2});
    tl.to("#s{pg}", {{ opacity:0, duration:0.5, ease:"sine.in" }}, {fe + 0.6});
    tl.set("#s{pg}", {{ visibility:"hidden" }}, {fe + 1.2});
"""
        t += dur

    # Assemble
        audio_html = ""
    if audio_path and os.path.exists(audio_path):
        rel_audio = os.path.relpath(audio_path, start=os.path.dirname(html_path))
        audio_html = f"<audio id=\"narration\" data-start=\"0\" data-duration=\"{total_dur}\" data-track-index=\"0\" src=\"{rel_audio}\" data-volume=\"1\"></audio>"
    gf_link = f'<link data-hf-fonts="true" href="{gf_url}" rel="stylesheet" />' if gf_url else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
{gf_link}
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{css_vars}{common_css}{scene_css}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total_dur}" data-width="1920" data-height="1080">
  {audio_html}
  <div class="bg-glow bg-glow-1"></div>
  {all_scenes}
  <div class="progress-bar">
    <div class="progress-track">
      <div class="progress-bg"></div>
      <div class="progress-fill" id="pf">
        <div class="dancer" id="pr"></div>
      </div>
    </div>
    <span class="progress-label" id="pl">1/{n}</span>
  </div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
tl.to(".bg-glow-1", {{ scale:1.1, opacity:0.6, duration:3, ease:"sine.inOut", yoyo:true, repeat:15 }}, 0);
tl.to("#pf", {{ width:'100%', duration:{total_dur}, ease:'linear' }}, 0);
{all_js}
window.__timelines["main"] = tl;
</script>
</body>
</html>"""


class CompositionHandler(StepHandler):
    """Element-driven HyperFrames composition engine."""
    name = "T6"
    description = "Element-driven HyperFrames composition"

    def execute(self):
        tl_path = self.episode_dir / "timeline.json"
        if not tl_path.exists():
            return StepResult(False, errors=[f"No timeline.json in {self.episode_dir}"])
        with open(tl_path) as f:
            timeline = json.load(f)
        slides = timeline.get("slides", [timeline] if isinstance(timeline, dict) else timeline)
        if isinstance(timeline, list):
            slides = timeline
        design = _load_design(str(self.episode_dir))
        total_dur = timeline.get("total_duration", sum(s.get("duration", 8) for s in slides))
        audio_path = str(self.episode_dir / "audio" / "narration.mp3")
        idx_path = self.episode_dir / "index.html"
        # Copy run_sprite.png if it exists in project root
        # Generate topic-appropriate sprite for progress bar
        import subprocess, json as jjson
        sprite_script = Path(__file__).resolve().parent.parent / "skills" / "bilibili-sprite-gen" / "scripts" / "generate_topic_sprite.py"
        state_path = self.episode_dir / "pipeline_state.json"
        topic = os.path.basename(str(self.episode_dir))
        if state_path.exists():
            with open(state_path) as sf:
                topic = jjson.load(sf).get("topic", topic)
        sprite_out = str(self.episode_dir / "run_sprite.png")
        print(f"  Generating sprite for topic: {topic[:40]}...")
        subprocess.run([
            "python3", str(sprite_script),
            "--topic", topic,
            "--out", sprite_out,
        ], capture_output=True, text=True, timeout=300)
        if os.path.exists(sprite_out):
            print(f"  Sprite generated: {os.path.getsize(sprite_out)} bytes")
        else:
            # Fallback: copy default sprite
            default = Path(__file__).resolve().parent.parent / "episodes" / "run_sprite_pixel.png"
            if default.exists():
                import shutil
                shutil.copy2(default, sprite_out)
        html = _render(design, slides, audio_path, str(idx_path))
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✅ Element-driven composition: {len(slides)} scenes, {total_dur}s")
        return StepResult(True, {"pages": len(slides), "total_duration": total_dur, "path": str(idx_path)})
