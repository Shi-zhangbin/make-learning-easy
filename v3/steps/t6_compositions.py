"""
v3/steps/t6_compositions.py — Element-driven HyperFrames engine

No fixed layouts. Each scene is an array of elements.
Each element type maps to a renderer + GSAP entrance animation.
All in one HyperFrames composition with push transitions + ambient.
"""
import json, os, shutil, re
from pathlib import Path
from v3.config import FILE_NAMES, resolve_episode_path
from v3.steps.base import StepHandler, StepResult
from v3.designs.base import load_preset
from v3.sprite_runner import get_runner_path, SPRITES_DIR_NAME, SPRITE_FILE_NAME, list_presets, make_preset_runner
from pathlib import Path

# Load GSAP locally to avoid CDN dependency
_GSAP_PATH = Path(__file__).resolve().parent.parent / "assets" / "gsap.min.js"
_GSAP_INLINE = _GSAP_PATH.read_text(encoding="utf-8") if _GSAP_PATH.exists() else ""


def _load_design(episode_dir):
    state_path = resolve_episode_path(episode_dir, "pipeline_state")
    style = "claude"
    if os.path.exists(state_path):
        with open(state_path) as f:
            s = json.load(f)
        style = s.get("design_style", "claude")
    try:
        return load_preset(style)
    except FileNotFoundError:
        return load_preset("claude")


def _render(design, slides, audio_path="", html_path="", sprite_style="boy"):
    """Element-driven HyperFrames composition generator."""

    # Sprite animation cycle speed per style (seconds per full frame cycle)
    SPRITE_CYCLE = {
        "boy": 1.2, "dino": 1.2, "walk": 1.8, "cycle": 0.9,
        "skateboard": 1.0, "jump": 0.7, "moonwalk": 1.5,
        "dance": 0.6, "fly": 0.8,
    }
    cycle_speed = SPRITE_CYCLE.get(sprite_style, 1.2)

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

    /* Sprite runner on progress bar */
    .dancer {{ position:absolute; bottom:-6px; left:-30px; width:60px; height:60px; background-image:url("sprites/runner.png"); background-size:540px 60px; image-rendering:auto; z-index:1000; pointer-events:none; }}

    .bg-glow {{ position:absolute; border-radius:50%; pointer-events:none; }}
    .bg-glow-1 {{ width:800px; height:800px; background:radial-gradient(circle,var(--accent)08 0%,transparent 70%); top:50%; left:50%; transform:translate(-50%,-50%); }}


    /* 3D: Ambient float particles — slow-moving decorative dots */
    .ambient-overlay {{ position:absolute; top:0; left:0; width:1920px; height:1080px; overflow:hidden; pointer-events:none; z-index:50; }}
    .ambient-dot {{ position:absolute; border-radius:50%; opacity:0.12; animation:ambientFloat var(--ad-dur,18s) ease-in-out infinite; }}
    .ambient-dot:nth-child(1) {{ width:8px; height:8px; left:10%; top:20%; --ad-dur:22s; animation-delay:-0s; }}
    .ambient-dot:nth-child(2) {{ width:14px; height:14px; left:80%; top:70%; --ad-dur:26s; animation-delay:-3s; }}
    .ambient-dot:nth-child(3) {{ width:6px; height:6px; left:30%; top:80%; --ad-dur:19s; animation-delay:-7s; }}
    .ambient-dot:nth-child(4) {{ width:10px; height:10px; left:65%; top:15%; --ad-dur:24s; animation-delay:-5s; }}
    .ambient-dot:nth-child(5) {{ width:5px; height:5px; left:50%; top:50%; --ad-dur:21s; animation-delay:-11s; }}
    .ambient-dot:nth-child(6) {{ width:12px; height:12px; left:88%; top:40%; --ad-dur:28s; animation-delay:-2s; }}
    .ambient-dot:nth-child(7) {{ width:4px; height:4px; left:15%; top:60%; --ad-dur:17s; animation-delay:-8s; }}
    .ambient-dot:nth-child(8) {{ width:9px; height:9px; left:42%; top:35%; --ad-dur:23s; animation-delay:-4s; }}
    @keyframes ambientFloat {{
        0% {{ transform: translate(0,0) scale(1); }}
        25% {{ transform: translate(30px,-20px) scale(1.1); }}
        50% {{ transform: translate(-10px,-40px) scale(0.9); }}
        75% {{ transform: translate(-35px,10px) scale(1.05); }}
        100% {{ transform: translate(0,0) scale(1); }}
    }}
    
    /* 3D: Subtle vignette overlay */
    .vignette {{ position:absolute; top:0; left:0; width:1920px; height:1080px; pointer-events:none; z-index:40; background:radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.20) 100%); }}
    
    /* Danmaku / bullet comments overlay */
    .danmaku-overlay {{ position:absolute; top:0; left:0; width:1920px; height:1080px; overflow:hidden; pointer-events:none; z-index:500; }}
    .danmaku {{ position:absolute; white-space:nowrap; font-family:"Noto Sans SC",sans-serif; font-size:22px; font-weight:700; color:var(--accent); text-shadow:0 0 8px rgba(0,0,0,0.3),0 0 2px white; opacity:0.7; animation:danmakuFly 8s linear forwards; }}
    .danmaku-1 {{ top:80px; animation-duration:9s; }}
    .danmaku-2 {{ top:160px; animation-duration:11s; animation-delay:2s; }}
    .danmaku-3 {{ top:600px; animation-duration:7s; animation-delay:4s; }}
    .danmaku-4 {{ top:720px; animation-duration:10s; animation-delay:1s; }}
    .danmaku-5 {{ top:240px; animation-duration:12s; animation-delay:6s; font-size:18px; color:var(--accent_amber); }}
    .danmaku-6 {{ top:380px; animation-duration:8s; animation-delay:3s; font-size:20px; color:var(--accent_blue); }}
    .danmaku-7 {{ top:850px; animation-duration:9s; animation-delay:5s; color:var(--accent_green); }}
    .danmaku-8 {{ top:450px; animation-duration:11s; animation-delay:7s; font-size:24px; color:var(--accent_amber); }}
    @keyframes danmakuFly {{
  0% {{ transform:translateX(1920px); opacity:0; }}
  5% {{ opacity:0.8; }}
  90% {{ opacity:0.8; }}
  100% {{ transform:translateX(-100%); opacity:0; }}
}}

    /* Comic speech bubble for highlights */
    .speech-bubble {{ position:relative; display:inline-block; background:var(--accent); color:white; border-radius:16px; padding:8px 16px; font-size:18px; font-weight:600; font-family:var(--hf); }}
    .speech-bubble::after {{ content:""; position:absolute; bottom:-8px; left:30px; border-left:8px solid transparent; border-right:8px solid transparent; border-top:8px solid var(--accent); }}

    /* Meme corner sticker */
    .meme-sticker {{ position:absolute; bottom:80px; right:20px; font-size:48px; z-index:888; opacity:0.5; pointer-events:none; }}

    /* Code block special: add a small tag */
    .code-tag {{ position:absolute; top:44px; right:28px; background:var(--accent); color:white; padding:2px 10px; border-radius:4px; font-size:11px; font-weight:600; text-transform:uppercase; z-index:10; }}
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
            src = el.get("src", "")
            # Resolve legacy "images/" paths to the configured images_dir (e.g. "05-images/")
            images_dir = FILE_NAMES.get("images_dir", "05-images")
            if src.startswith("images/"):
                src = images_dir + src[len("images"):]
            elif src and "/" not in src and not src.startswith("data:"):
                src = images_dir + "/" + src
            # Adaptive container: width determined by flex layout, height auto-calculated
            # from 16:9 aspect ratio so images fill available space without blank gaps
            size_css = {"small": "flex:0.6; aspect-ratio:16/9;",
                        "medium": "flex:1; aspect-ratio:16/9;",
                        "large": "flex:1.5; aspect-ratio:16/9;",
                        "fill": "flex:1; min-height:100px;"}.get(sz, "flex:1; aspect-ratio:16/9;")
            if sz == "fill":
                return f'<div class="img-wrap" style="{size_css}"><img src="{src}" alt=""></div>'
            return f'<div class="img-wrap" style="{size_css}"><img src="{src}" alt=""></div>'
        elif t == "code":
            lines = el.get("code", el.get("text", ""))
            tag = el.get("lang", "")
            tag_html = f'<div class="code-tag">{tag}</div>' if tag else ""
            return f'<div class="code-w" style="flex:1"><div class="ch"><span class="cd" style="background:#ff5f56;"></span><span class="cd" style="background:#ffbd2e;"></span><span class="cd" style="background:#27c93f;"></span><span style="margin-left:10px;font-family:monospace;font-size:12px;color:#888;">{tag}</span></div>{tag_html}<div class="cb">{lines}</div></div>'
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
        elif t == "speech-bubble":
            return f'<div style="display:flex;gap:12px;align-items:center;max-width:70%;"><div class="speech-bubble" style="background:var(--accent);color:white;border-radius:16px;padding:12px 20px;font-size:22px;font-weight:600;font-family:var(--hf);">{el.get("text","")}</div></div>'
        elif t == "button":
            return f'<div style="display:flex;justify-content:center;margin-top:8px;"><div class="badge" style="border:2px solid var(--accent);background:transparent;padding:8px 28px;border-radius:999px;cursor:default;">{el.get("text","")}</div></div>'
        return ""

    # Element entrance animation pool (3A) — deterministic variety per element type
    def entrance_for(elem, pg, t, idx):
        """Generate a GSAP entrance animation with deterministic variety."""
        etype = elem.get("type", "")
        delay = t + 0.15 + idx * 0.08
        # Deterministic seed from page and element index
        _seed = (pg * 7 + idx * 13) % 3

        # Each type has 3 animation variants; variant 0 = original single style
        variants = {
            "badge": [
                'y:12,opacity:0,duration:0.3',
                'x:-10,opacity:0,duration:0.3',
                'scale:0.8,opacity:0,duration:0.35',
            ],
            "heading": [
                'y:25,opacity:0,duration:0.5',
                'x:-20,opacity:0,duration:0.45',
                'scale:0.92,opacity:0,duration:0.45',
            ],
            "paragraph": [
                'y:15,opacity:0,duration:0.4',
                'x:12,opacity:0,duration:0.35',
                'opacity:0,duration:0.3',
            ],
            "accent-line": [
                'scaleX:0,opacity:0,duration:0.4',
                'scaleX:0,opacity:0,duration:0.3,transformOrigin:"left center"',
                'scaleX:0,opacity:0,duration:0.5',
            ],
            "spacer": ['opacity:0,duration:0.01'] * 3,
            "chip-row": [
                'y:12,opacity:0,duration:0.3',
                'x:-10,opacity:0,duration:0.3',
                'scale:0.9,opacity:0,duration:0.3',
            ],
            "image": [
                'scale:0.95,opacity:0,duration:0.5',
                'opacity:0,rotation:-2,duration:0.5',
                'scale:0.9,opacity:0,duration:0.4,transformOrigin:"center center"',
            ],
            "code": [
                'x:-15,opacity:0,duration:0.5',
                'y:10,opacity:0,duration:0.4',
                'scale:0.95,opacity:0,duration:0.4',
            ],
            "split": [
                'opacity:0,duration:0.4',
                'x:-10,opacity:0,duration:0.35',
                'opacity:0,scale:0.98,duration:0.35',
            ],
            "fq-row": [
                'y:15,opacity:0,duration:0.4',
                'x:10,opacity:0,duration:0.35',
                'scale:0.95,opacity:0,duration:0.35',
            ],
            "quote": [
                'y:15,opacity:0,duration:0.5',
                'x:-10,opacity:0,duration:0.4',
                'scale:0.95,opacity:0,duration:0.4',
            ],
            "button": [
                'scale:0.9,opacity:0,duration:0.4',
                'y:10,opacity:0,duration:0.35',
                'opacity:0,duration:0.3',
            ],
            "speech-bubble": [
                'scale:0.85,opacity:0,duration:0.5',
                'y:10,opacity:0,duration:0.4',
                'x:-8,opacity:0,duration:0.4',
            ],
        }
        pool = variants.get(etype, ['y:12,opacity:0,duration:0.3'])
        props = pool[_seed] if _seed < len(pool) else pool[0]
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
      <!-- 3D: Ambient float particles + vignette overlay -->
      <div class="ambient-overlay">
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
        <div class="ambient-dot" style="background:var(--accent);"></div>
      </div>
      <div class="vignette"></div>
      <div style="display:none;"></div>
    </div>
  </div>"""
        all_js += js

        if i < n - 1:
            nt = t + dur
            # Scene transition variety (B010)
            _t = i % 5
            if _t == 0:
                _oa = f'tl.to("#s{pg}", {{ y:-1080, duration:{trans}, ease:"power3.inOut" }}, {nt})'
                _ia = f'tl.fromTo("#s{pg+1}", {{ y:1080, opacity:0 }}, {{ y:0, opacity:1, duration:{trans}, ease:"power3.inOut" }}, {nt})'
            elif _t == 1:
                _oa = f'tl.to("#s{pg}", {{ scale:0.8, opacity:0, duration:{trans}, ease:"power2.inOut" }}, {nt})'
                _ia = f'tl.fromTo("#s{pg+1}", {{ scale:1.15, opacity:0 }}, {{ scale:1, opacity:1, duration:{trans}, ease:"power2.out" }}, {nt})'
            elif _t == 2:
                _oa = f'tl.to("#s{pg}", {{ x:-1920, duration:{trans}, ease:"power3.inOut" }}, {nt})'
                _ia = f'tl.fromTo("#s{pg+1}", {{ x:1920, opacity:0 }}, {{ x:0, opacity:1, duration:{trans}, ease:"power3.inOut" }}, {nt})'
            elif _t == 3:
                _oa = f'tl.to("#s{pg}", {{ scale:1.15, rotation:4, opacity:0, duration:{trans}, ease:"power2.in" }}, {nt})'
                _ia = f'tl.fromTo("#s{pg+1}", {{ scale:0.9, rotation:-4, opacity:0 }}, {{ scale:1, rotation:0, opacity:1, duration:{trans}, ease:"power2.out" }}, {nt})'
            else:
                _oa = f'tl.to("#s{pg}", {{ opacity:0, duration:{trans*0.6}, ease:"sine.inOut" }}, {nt})'
                _ia = f'tl.fromTo("#s{pg+1}", {{ opacity:0 }}, {{ opacity:1, duration:{trans*0.6}, ease:"sine.inOut" }}, {nt})'
            all_js += f"""    {_oa};
    {_ia};
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
<script>/* inlined: assets/gsap.min.js */
{_GSAP_INLINE}</script>
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
      <div class="progress-fill" id="pf"></div>
      <div class="dancer" id="pr"></div>
    </div>
    <span class="progress-label" id="pl">1/{n}</span>
  </div>
  <!-- Danmaku overlay -->
  <div class="danmaku-overlay">
    <div class="danmaku danmaku-1">学到了！</div>
    <div class="danmaku danmaku-2">哈哈真实</div>
    <div class="danmaku danmaku-3">妙啊</div>
    <div class="danmaku danmaku-4">就这？</div>
    <div class="danmaku danmaku-5">是我了</div>
    <div class="danmaku danmaku-6">这也太真实了</div>
    <div class="danmaku danmaku-7">已三连</div>
    <div class="danmaku danmaku-8">下次一定</div>
  </div>
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
tl.to(".bg-glow-1", {{ scale:1.1, opacity:0.6, duration:3, ease:"sine.inOut", yoyo:true, repeat:15 }}, 0);
tl.to("#pf", {{ width:'100%', duration:{total_dur}, ease:'linear' }}, 0);
tl.to("#pr", {{ left:'calc(100% - 30px)', duration:{total_dur}, ease:'linear' }}, 0);
const _sc = {cycle_speed}, _sf = 9;
tl.to("#pr", {{ duration:{total_dur}, ease:'none', onUpdate:function(){{ let f=Math.floor((this.time()%_sc)/_sc*_sf); this.targets()[0].style.backgroundPosition='-'+f*60+'px 0px'; }} }}, 0);
{all_js}
window.__timelines["main"] = tl;
</script>
</body>
</html>"""



def _page_spec_to_elements(spec):
    """Convert a PageSpec to element-list format for _render().
    
    Maps each of the 10 layouts (hero, concept, flipped, comparison, code_block,
    flowchart, card_grid, quote, section_divider, outro) to distinct visual
    element structures so every page has a unique layout.
    """
    from v3.pagespec import PageSpec, Section
    elements = []

    # ── Badge ──
    if spec.badge:
        elements.append({"type": "badge", "text": spec.badge})

    # ── Title (xl for hero/divider, lg otherwise) ──
    title_text = f"{spec.emoji} {spec.title}" if spec.emoji else spec.title
    title_size = "xl" if spec.layout in ("hero", "section_divider") else "lg"
    elements.append({"type": "heading", "size": title_size, "text": title_text})

    # ── Subtitle ──
    if spec.subtitle:
        elements.append({"type": "paragraph", "text": spec.subtitle})

    # ── Accent line for hero/section_divider ──
    if spec.layout in ("hero", "section_divider"):
        elements.append({"type": "accent-line"})

    # ── Chip tags for hero ──
    if spec.layout == "hero":
        elements.append({"type": "chip-row", "chips": ["入门科普", "程序员日常", "10分钟"]})

    # ── Layout-specific content ──

    if spec.layout == "comparison":
        for s in spec.sections:
            if s.comparison:
                left_items = []
                for item in s.comparison.left_items:
                    left_items.append({"type": "card-alt", "title": item, "desc": "", "icon": "\u2022", "tag": ""})
                right_items = []
                for item in s.comparison.right_items:
                    right_items.append({"type": "card-alt", "title": item, "desc": "", "icon": "\u2022", "tag": ""})
                elements.append({
                    "type": "split",
                    "left": [{"type": "heading", "size": "sm", "text": s.comparison.left_title}] + left_items,
                    "right": [{"type": "heading", "size": "sm", "text": s.comparison.right_title}] + right_items,
                })

    elif spec.layout == "code_block":
        code_text = ""
        code_lang = "python"
        cards = []
        for s in spec.sections:
            if s.code:
                code_text = "\n".join(s.code.lines) if hasattr(s.code, 'lines') else str(s.code)
            for c in s.cards:
                cards.append({"icon": c.icon, "title": c.title, "desc": c.body, "tag": ""})
        left = [{"type": "code", "code": code_text, "lang": code_lang}] if code_text else []
        right = [{"type": "card-alt-row", "cards": cards}] if cards else []
        if left or right:
            elements.append({"type": "split", "left": left, "right": right,
                             "left_weight": 1.4, "right_weight": 1})

    elif spec.layout in ("concept", "flipped"):
        cards = []
        for s in spec.sections:
            for c in s.cards:
                cards.append({"icon": c.icon, "title": c.title, "body": c.body})

        # image_position from PageSpec (set by page-plans or heuristic)
        img_pos = getattr(spec, "image_position", "right") or "right"

        if img_pos == "left":
            # Image on left, cards on right (flipped-style)
            left = [{"type": "image", "src": spec.image_slot, "size": "medium"}] if spec.image_slot else []
            alt_cards = [{"icon": c["icon"], "title": c["title"], "desc": c["body"], "tag": ""} for c in cards]
            right = [{"type": "card-alt-row", "cards": alt_cards}] if alt_cards else []
        elif img_pos == "bottom":
            # Stack: cards on top, image below
            if cards:
                elements.append({"type": "card-row", "cards": cards[:3]})
            if spec.image_slot:
                elements.append({"type": "image", "src": spec.image_slot, "size": "medium"})
            left, right = None, None  # skip split
        elif img_pos == "background":
            # Full-page background — not fully supported yet, fallback to right
            left = [{"type": "card-row", "cards": cards[:3]}] if cards else []
            right = [{"type": "image", "src": spec.image_slot, "size": "medium"}] if spec.image_slot else []
        else:
            # Default: image on right (concept-style)
            left = [{"type": "card-row", "cards": cards[:3]}] if cards else []
            right = [{"type": "image", "src": spec.image_slot, "size": "medium"}] if spec.image_slot else []

        if left is not None and right is not None and (left or right):
            elements.append({"type": "split", "left": left, "right": right})

    elif spec.layout == "flowchart":
        for s in spec.sections:
            if s.cards:
                elements.append({
                    "type": "card-alt-row",
                    "cards": [{"icon": c.icon, "title": c.title, "desc": c.body, "tag": f"Step{i+1}"}
                              for i, c in enumerate(s.cards)]
                })
        if spec.image_slot:
            elements.append({"type": "image", "src": spec.image_slot, "size": "medium"})

    elif spec.layout == "card_grid":
        for s in spec.sections:
            if s.cards:
                elements.append({
                    "type": "grid-2x2",
                    "cards": [{"icon": c.icon, "title": c.title, "body": c.body} for c in s.cards[:4]]
                })
        if spec.image_slot:
            elements.append({"type": "image", "src": spec.image_slot, "size": "medium"})

    elif spec.layout == "quote":
        for s in spec.sections:
            if s.quote_text:
                elements.append({
                    "type": "quote",
                    "text": s.quote_text,
                    "author": s.quote_author or ""
                })

    elif spec.layout == "outro":
        for s in spec.sections:
            if s.cards:
                elements.append({
                    "type": "card-row",
                    "cards": [{"icon": c.icon, "title": c.title, "body": c.body} for c in s.cards[:3]]
                })
        elements.append({"type": "speech-bubble", "text": "我们下期见！"})

    # ── Bottom image for hero/section_divider ──
    if spec.layout in ("hero", "section_divider"):
        if spec.image_slot:
            elements.append({"type": "image", "src": spec.image_slot, "size": "medium"})

    return elements



def _try_load_page_plans(episode_dir, slides, images):
    """Try to load 02-page-plans.json and convert to PageSpec list.
    Returns None if file doesn't exist or is invalid (triggers fallback to heuristic)."""
    from v3.config import FILE_NAMES
    plans_path = Path(episode_dir) / FILE_NAMES.get("page_plans", "02-page-plans.json")

    if not plans_path.exists():
        return None

    try:
        raw = json.loads(plans_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        print("  \u26a0\ufe0f  02-page-plans.json 解析失败，降级到 heuristic")
        return None

    pages_data = raw.get("pages", [])
    if not pages_data:
        return None

    valid_layouts = {"hero", "concept", "flipped", "comparison", "code_block",
                     "flowchart", "card_grid", "quote", "section_divider", "outro"}

    from v3.pagespec import PageSpec, Section, Card as PSCard, CodeBlock, ComparisonGroup

    specs = []
    prev_surface = ""

    surface_order = ["cream", "cream_soft", "cream_card", "cream_soft"]

    for i, pg_data in enumerate(pages_data):
        pg = pg_data.get("page", i + 1)
        layout = pg_data.get("layout", "concept")
        if layout not in valid_layouts:
            layout = "concept"

        slide = slides[i] if i < len(slides) else {}

        # Match image file from 05-images/
        img_fn = _match_image(pg, images)

        # Build sections from page-plan data
        sections = []
        cards_data = pg_data.get("cards") or []
        if cards_data:
            cards = [PSCard(icon=c.get("icon", ""), title=c.get("title", ""),
                            body=c.get("body", ""), style="light") for c in cards_data]
            sections.append(Section(style="cream_card", cards=cards))

        code_data = pg_data.get("code")
        if code_data:
            code_body = code_data.get("body", "")
            code_lang = code_data.get("language", "python")
            sections.append(Section(
                style="dark",
                code=CodeBlock(lines=code_body.split("\n"), language=code_lang)))

        comparison_data = pg_data.get("comparison")
        if comparison_data:
            sections.append(Section(
                style="cream_card",
                comparison=ComparisonGroup(
                    left_title=comparison_data.get("left_title", ""),
                    left_items=comparison_data.get("left_items", []),
                    right_title=comparison_data.get("right_title", ""),
                    right_items=comparison_data.get("right_items", []),
                )))

        flow_data = pg_data.get("flow_steps")
        if flow_data:
            step_cards = [PSCard(icon=s.get("icon", ""), title=s.get("title", ""),
                                 body=s.get("body", ""), style="light") for s in flow_data]
            sections.append(Section(style="cream_card", cards=step_cards))

        quote_data = pg_data.get("quote")
        if quote_data:
            if isinstance(quote_data, str):
                sections.append(Section(style="dark", quote_text=quote_data, quote_author=""))
            elif isinstance(quote_data, dict):
                sections.append(Section(style="dark",
                    quote_text=quote_data.get("text", ""),
                    quote_author=quote_data.get("author", "")))

        # Surface alternation
        if not prev_surface or prev_surface == "dark":
            surface = surface_order[0]
        else:
            idx = surface_order.index(prev_surface) if prev_surface in surface_order else 0
            surface = surface_order[(idx + 1) % len(surface_order)]
        prev_surface = surface

        # Image position from page-plan
        img_info = pg_data.get("image") or {}
        img_pos = img_info.get("position", "right") if isinstance(img_info, dict) else "right"

        # Emoji
        emoji = pg_data.get("emoji", "")
        if not emoji:
            kw_map = {"概念": "\U0001f9e0", "对比": "\u2696\ufe0f", "流程": "\U0001f504",
                      "代码": "\U0001f4bb", "总结": "\U0001f3af", "核心": "\U0001f4a1", "关键": "\U0001f511"}
            title = pg_data.get("heading", "")
            emoji = next((v for k, v in kw_map.items() if k in title), "\U0001f4a1")

        # Badge label
        badge_prefix = {"hero": "开场", "outro": "总结", "section_divider": "章节",
                        "comparison": "对比", "code_block": "代码实践", "flowchart": "流程",
                        "card_grid": "要点", "quote": "引述", "concept": "核心概念", "flipped": "深入理解"}
        bp = badge_prefix.get(layout, "章节")
        badge = pg_data.get("badge", f"{bp} {pg}")

        spec = PageSpec(
            layout=layout,
            page_num=pg,
            total_pages=len(pages_data),
            duration=slide.get("duration", 10),
            start=slide.get("start", 0),
            surface=surface,
            badge=badge,
            title=pg_data.get("heading", ""),
            subtitle=pg_data.get("subtitle") or "",
            emoji=emoji,
            sections=sections,
            image_slot=img_fn,
            image_position=img_pos,
        )
        specs.append(spec)

    return specs


def _match_image(page_num, images):
    """Match an image filename to a page number, or return empty string."""
    for fn in images:
        if f"p{page_num:02d}" in fn.lower() or f"P{page_num:02d}" in fn:
            return fn
    return ""

class CompositionHandler(StepHandler):
    """Element-driven HyperFrames composition engine."""
    name = "T6"
    description = "Element-driven HyperFrames composition"


    def pre_condition(self):
        """Verify timeline has enough slides for composition."""
        err = super().pre_condition()
        if err:
            return err
        tl_path = self.episode_dir / FILE_NAMES["timeline"]
        if not tl_path.exists():
            return f"timeline.json 不存在 ({tl_path})。请先运行 T3 生成配音和时间线。"
        import json
        with open(tl_path) as f:
            timeline = json.load(f)
        slides = timeline.get("slides", [])
        if len(slides) < 5:
            return (
                f"timeline.json 只有 {len(slides)} 个 slide，需要至少 5 个。\n"
                f"脚本中的分页标记不足，请检查 02-script.txt 中的 --- P1, --- P2 等标记。"
            )
        return None

    def execute(self):
        tl_path = self.episode_dir / FILE_NAMES["timeline"]
        if not tl_path.exists():
            return StepResult(False, errors=[f"No timeline.json in {self.episode_dir}"])
        with open(tl_path) as f:
            timeline = json.load(f)
        slides = timeline.get("slides", [timeline] if isinstance(timeline, dict) else timeline)
        if isinstance(timeline, list):
            slides = timeline

        # ══════════ PageSpec bridge: narration → layout → elements ══════════
        # Ensure each slide has narration (fallback: parse script directly)
        has_narration = any(s.get("narration") for s in slides)
        if not has_narration:
            script_path = self.episode_dir / FILE_NAMES["script"]
            if script_path.exists():
                raw = script_path.read_text(encoding="utf-8")
                pp = re.compile(r"---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL)
                for m in pp.finditer(raw):
                    pg = int(m.group(1))
                    for slide in slides:
                        if slide.get("page") == pg:
                            slide["narration"] = m.group(2).strip()
                            break

        # Collect available images
        images_dir = self.episode_dir / FILE_NAMES["images_dir"]
        images = {}
        if images_dir.exists():
            for f in sorted(images_dir.iterdir()):
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                    images[f.name] = f.name

        # Try model-driven layout from 02-page-plans.json first
        specs = _try_load_page_plans(str(self.episode_dir), slides, images)
        if specs is not None:
            print(f"  \U0001f4d0 Using model-driven layout from 02-page-plans.json")
        else:
            # Fallback: heuristic layout selection via pagespec
            from v3.pagespec import build_all_pages
            specs = build_all_pages(slides, images)
            print(f"  \U0001f4d0 Using heuristic layout selection (no page-plans)")

        # Convert PageSpecs to elements and attach to slides
        for slide, spec in zip(slides, specs):
            slide["elements"] = _page_spec_to_elements(spec)

        # Print layout summary
        layout_counts = {}
        for spec in specs:
            layout_counts[spec.layout] = layout_counts.get(spec.layout, 0) + 1
        layout_summary = ", ".join(f"{k}:{v}" for k, v in sorted(layout_counts.items()))
        print(f"  \U0001f4d0 Layouts: {layout_summary}")

        # ══════════ end bridge ══════════
        design = _load_design(str(self.episode_dir))
        total_dur = timeline.get("total_duration", sum(s.get("duration", 8) for s in slides))
        audio_path = str(self.episode_dir / FILE_NAMES["audio_narration"])
        idx_path = self.episode_dir / FILE_NAMES["composition"]

        # Resolve sprite runner for the episode
        sprites_dir = self.episode_dir / SPRITES_DIR_NAME
        sprites_dir.mkdir(parents=True, exist_ok=True)
        dst_sprite = sprites_dir / SPRITE_FILE_NAME

        # Check if pipeline state specifies a sprite style
        sprite_style = None
        state_path_resolved = resolve_episode_path(str(self.episode_dir), "pipeline_state")
        if os.path.exists(state_path_resolved):
            with open(state_path_resolved) as _sf:
                _state = json.load(_sf)
            sprite_style = _state.get("sprite_style")

        if sprite_style and sprite_style in list_presets():
            # Generate sprite for this style
            print(f"  🎨 Generating sprite style: {sprite_style}")
            make_preset_runner(sprite_style, str(dst_sprite), timeout=300)
        else:
            # Use existing sprite (from asset or previous generation)
            src_sprite = get_runner_path(str(self.episode_dir))
            if os.path.exists(src_sprite) and src_sprite != str(dst_sprite):
                shutil.copy2(src_sprite, dst_sprite)
                print(f"  🏃 Sprite runner: {dst_sprite.name}")
            elif not os.path.exists(src_sprite):
                print(f"  ⚠️ No sprite runner found at {src_sprite}")

        html = _render(design, slides, audio_path, str(idx_path), sprite_style)
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(html)
        # Create index.html symlink/copy for HyperFrames compatibility
        idx_link = self.episode_dir / "index.html"
        if not idx_link.exists():
            import shutil
            shutil.copy2(str(idx_path), str(idx_link))
            print(f"  🔗 Created index.html -> 06-composition.html")
        print(f"  ✅ Element-driven composition: {len(slides)} scenes, {total_dur}s")
        return StepResult(True, {"pages": len(slides), "total_duration": total_dur, "path": str(idx_path)})
