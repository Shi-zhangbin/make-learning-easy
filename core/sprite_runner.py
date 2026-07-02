"""
core/sprite_runner.py — Progress bar running character (sprite sheet)

Generates a 3x3 grid sprite sheet via AI, processes it into a horizontal strip
for the video progress bar running animation.

Usage:
    # Generate from a preset style
    python3 -m core.sprite_runner preset --style boy --out core/assets/sprite_runner.png

    # Process existing grid into strip
    python3 -m core.sprite_runner process --in grid.png --out strip.png
"""
import argparse, os
from pathlib import Path

from PIL import Image

from core.config import CORE_DIR as V3_DIR
from core.imagegen import _wuyinkeji_generate

# ── Constants ──
DEFAULT_FRAMES = 9
DEFAULT_FRAME_SIZE = 60
ASSETS_DIR = Path(V3_DIR) / "assets" / "sprites"
SPRITES_DIR_NAME = "sprites"
SPRITE_FILE_NAME = "runner.png"  # legacy fallback

def _preset_path(style: str) -> Path:
    """Return the canonical asset path for a given sprite preset."""
    return ASSETS_DIR / f"{style}.png"

def _episode_path(episode_dir: str, style: str) -> Path:
    """Return the episode-local path for a given sprite style."""
    return Path(episode_dir) / SPRITES_DIR_NAME / f"{style}.png"

# ── Animation cycle templates (shared quality rules + 9-frame descriptions) ──
# Each template enforces: identical character, no bounce, smooth loop, white bg
ANIMATION_CYCLES = {
    "run": (
        "9-frame running cycle. Each cell is a DISTINCT pose — "
        "all limbs move: legs alternate, arms swing opposite to legs, "
        "head and torso bob slightly with each stride.\n"
        "Cell 9 → cell 1 loop is a continuous cycle.\n"
        "Cell 1: left foot landing forward, right foot trailing behind, "
        "right arm forward, left arm back.\n"
        "Cell 2: left foot flat, weight over, right leg coming through, "
        "arms at sides.\n"
        "Cell 3: both legs passing under body, right leg mid-swing, "
        "arms starting to swap positions.\n"
        "Cell 4: right leg reaching forward, left leg pushing off, "
        "left arm forward, right arm back.\n"
        "Cell 5: right foot landing forward, left foot trailing, "
        "arms fully swapped.\n"
        "Cell 6: right foot flat, weight over, left leg coming through, "
        "arms at sides again.\n"
        "Cell 7: both legs passing again, left leg mid-swing, "
        "arms starting to swap.\n"
        "Cell 8: left leg reaching forward, right leg pushing off, "
        "right arm forward.\n"
        "Cell 9: left leg reaching forward mid-air about to land — "
        "DIFFERENT pose from cell 1 which has already landed. "
        "Loop: cell 9 (airborne) → cell 1 (landed)."
    ),

    "typing": (
        "9-frame cat typing on computer cycle. Each cell is a DISTINCT pose — "
        "a ginger tabby cat sits at a desk in front of a computer, "
        "paws move to press keys, tail curls behind, "
        "pointy ears and round head above the screen, "
        "orange fur with tabby stripes.\n"
        "Cell 9 → cell 1 loop repeats continuously.\n"
        "Cell 1: cat sitting upright, both paws hovering above keyboard, "
        "looking at screen.\n"
        "Cell 2: left paw pressing down on keyboard, right paw hovering, "
        "body leaning forward slightly.\n"
        "Cell 3: right paw pressing down, left paw lifting up.\n"
        "Cell 4: both paws tapping quickly, tail tip twitching.\n"
        "Cell 5: pause — both paws off keys, head tilts slightly at screen.\n"
        "Cell 6: both paws starting to stretch upward, "
        "body beginning to lean back, mouth starting to open.\n"
        "Cell 7: full stretch — both paws way up above keyboard, "
        "back arched, mouth wide open in big yawn, eyes squinting.\n"
        "Cell 8: paws coming down to keyboard level, "
        "fingers about to touch keys.\n"
        "Cell 9: paws landing on keyboard, touching the keys — "
        "DIFFERENT from cell 1 (paws on keys vs hovering above). "
        "Loop: cell 9 (landed) → cell 1 (hovering, about to type)."
    ),
    "run-dino": (
        "9-frame dinosaur running cycle. Each cell is a DISTINCT pose — "
        "full body in motion: short legs take quick steps, "
        "large head bobs up and down with each stride, "
        "long tail bounces opposite to the legs for balance, "
        "tiny arms held out and slightly up for stability.\n"
        "Cell 9 → cell 1 loop is a continuous cycle.\n"
        "Cell 1: left foot stepping forward landing, right foot trailing, "
        "head up, tail lifted behind, tiny arms spread.\n"
        "Cell 2: left foot flat on ground, body shifts forward over it, "
        "tail starts lowering, head centers.\n"
        "Cell 3: both feet passing under round body, "
        "head bobbing down slightly, tail at lowest point.\n"
        "Cell 4: right foot reaching forward landing, left foot behind, "
        "tail starting to lift again, head up.\n"
        "Cell 5: right foot flat, body forward, "
        "tail lifted behind, arms out for balance.\n"
        "Cell 6: both feet passing again under body, "
        "head dips, tail lowers.\n"
        "Cell 7: left foot starting forward, right foot pushing, "
        "tail lifts, head rises.\n"
        "Cell 8: left foot reaching forward, tail at highest point, "
        "head fully up.\n"
        "Cell 9: left foot about to land, tail starting to drop — "
        "DIFFERENT from cell 1. Loop: cell 9 → cell 1 is seamless."
    ),
    }

# ── Shared prompt builder ──
_BASE_QUALITY = (
    "CRITICAL: IDENTICAL character SIZE, POSITION and HEIGHT in all 9 cells. "
    "All 9 cells MUST be distinctly different poses — "
    "this is a full animation cycle, NOT 9 similar drawings. "
    "Every limb moves: legs, arms, head, and torso all change position per cell. "
    "Cell 9 must be DIFFERENT from cell 1 but flow seamlessly into it for looping. "
    "No vertical bouncing. Minimal pixel change between consecutive cells. "
    "Simple flat vector pixel art, thick outlines, white background."
)

def _build_grid_prompt(character_desc: str, anim_type: str) -> str:
    """Build a complete grid prompt from character description + animation type."""
    cycle = ANIMATION_CYCLES.get(anim_type, ANIMATION_CYCLES["run"])
    return (
        f"A 3x3 sprite sheet, 9 cells, ONE {character_desc} "
        f"side-view {anim_type} animation, pixel art, white background. "
        f"{_BASE_QUALITY}\n"
        f"{cycle}"
    )

# ── Sprite Presets (each just specifies character + animation type) ──
SPRITE_PRESETS = {
    "boy":    {"name": "小男孩",  "desc": "Cute chibi boy running",        "anim_type": "run",        "char": "cute chibi boy"},
    "dino":   {"name": "小恐龙",  "desc": "Cute blue dinosaur running",    "anim_type": "run-dino",   "char": "baby blue dinosaur with round body, tiny arms, very big head, long bouncy tail, short legs"},
    
    
    
    
    
    
    
    
    "cat":    {"name": "打字猫",  "desc": "Cat typing on computer","anim_type": "typing","char": "ginger tabby orange cat with round head and pointy ears sitting at desk with computer screen and keyboard"},
}


# ══════════════════════════════════════════════════════════════════
# Image processing helpers
# ══════════════════════════════════════════════════════════════════

def _detect_background(img: Image.Image) -> tuple[int, int, int]:
    """Detect the most likely background color from the frame corners."""
    w, h = img.size
    margin = min(5, w // 5, h // 5)
    samples = []
    for x_off in range(margin):
        for y_off in range(margin):
            samples.append(img.getpixel((x_off, y_off))[:3])
            samples.append(img.getpixel((w - 1 - x_off, y_off))[:3])
            samples.append(img.getpixel((x_off, h - 1 - y_off))[:3])
            samples.append(img.getpixel((w - 1 - x_off, h - 1 - y_off))[:3])
    from collections import Counter
    quantized = [(r // 16 * 16, g // 16 * 16, b // 16 * 16) for r, g, b in samples]
    most_common = Counter(quantized).most_common(1)[0][0]
    return (most_common[0] + 8, most_common[1] + 8, most_common[2] + 8)


def _remove_background(img: Image.Image, bg_color: tuple[int, int, int], threshold: int = 50) -> Image.Image:
    """Make all pixels close to bg_color transparent."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if abs(r - bg_color[0]) + abs(g - bg_color[1]) + abs(b - bg_color[2]) < threshold:
                pixels[x, y] = (r, g, b, 0)
    return rgba


def _autocrop(img: Image.Image, padding: int = 2) -> Image.Image:
    """Crop transparent borders from a PIL image."""
    bbox = img.getbbox()
    if bbox:
        x0 = max(0, bbox[0] - padding)
        y0 = max(0, bbox[1] - padding)
        x1 = min(img.width, bbox[2] + padding)
        y1 = min(img.height, bbox[3] + padding)
        return img.crop((x0, y0, x1, y1))
    return img


# ══════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════

def list_presets() -> list[str]:
    """Return available sprite preset names."""
    return list(SPRITE_PRESETS.keys())


def generate_sprite(prompt: str, output_path: str = "", timeout: int = 180) -> str:
    """Generate a 3x3 sprite grid via wuyinkeji API."""
    if not output_path:
        output_path = str(Path.cwd() / "run_sprite_grid.png")
    print(f"  🎨 Generating sprite...")
    img_data = _wuyinkeji_generate(prompt, size="1:1", timeout=timeout)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        f.write(img_data)
    print(f"  ✅ Grid saved: {out} ({len(img_data)//1024}KB)")
    return str(out)


def process_grid_sprite(
    input_path: str, output_path: str,
    grid_cols: int = 3, grid_rows: int = 3,
    frame_size: int = DEFAULT_FRAME_SIZE,
) -> str:
    """Extract frames from a grid sprite sheet, remove background,
    center-align via visual center, resize uniformly, and assemble into strip."""
    img = Image.open(input_path).convert("RGBA")
    fw, fh = img.width // grid_cols, img.height // grid_rows

    # Step 1: Extract frames (raw, before any processing)
    raw_frames_raw = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            frame = img.crop((col * fw, row * fh, (col + 1) * fw, (row + 1) * fh))
            raw_frames_raw.append(frame)

    # Step 1a: Detect global background color across ALL frames
    # Sample corner pixels from every frame and find the majority color
    all_samples = []
    for f in raw_frames_raw:
        for dx in range(5):
            for dy in range(5):
                for px, py in [(dx, dy), (fw-1-dx, dy), (dx, fh-1-dy), (fw-1-dx, fh-1-dy)]:
                    r, g, b, a = f.getpixel((px, py))
                    if a > 50:  # only consider non-transparent corner pixels
                        all_samples.append((r // 8 * 8, g // 8 * 8, b // 8 * 8))
    from collections import Counter
    global_bg_q = Counter(all_samples).most_common(1)[0][0]
    global_bg = (global_bg_q[0] + 4, global_bg_q[1] + 4, global_bg_q[2] + 4)

    # Step 1b: Remove background using GLOBAL color with aggressive threshold
    # Also set ANY pixel with near-bg color to transparent, not just corners
    raw_frames = []
    for f in raw_frames_raw:
        rgba = f.convert("RGBA")
        pixels = rgba.load()
        for y in range(fh):
            for x in range(fw):
                r, g, b, a = pixels[x, y]
                # Aggressive: pixels near background color OR near-white with low alpha
                diff = abs(r - global_bg[0]) + abs(g - global_bg[1]) + abs(b - global_bg[2])
                is_near_white = (r > 200 and g > 200 and b > 200)
                if diff < 80 or (is_near_white and a < 200):
                    pixels[x, y] = (r, g, b, 0)
        raw_frames.append(rgba)

    # Step 1.5: Align all frames by centroid (horizontal + vertical)
    # Keep the full canvas size during alignment. After alignment,
    # find a common bounding box so the crop is uniform.
    centroids = []
    for f in raw_frames:
        total_mass = 0
        cx = cy = 0
        for y in range(f.height):
            for x in range(f.width):
                a = f.getpixel((x, y))[3]
                if a > 0:
                    total_mass += a
                    cx += x * a
                    cy += y * a
        if total_mass > 0:
            centroids.append((cx / total_mass, cy / total_mass))
        else:
            centroids.append((f.width / 2, f.height / 2))

    # Target centroids = average of all frames (both horizontal and vertical)
    avg_cx = sum(c[0] for c in centroids) / len(centroids)
    avg_cy = sum(c[1] for c in centroids) / len(centroids)

    aligned = []
    for i, f in enumerate(raw_frames):
        dx = int(avg_cx - centroids[i][0])
        dy = int(avg_cy - centroids[i][1])
        c = Image.new("RGBA", (f.width, f.height), (0, 0, 0, 0))
        c.paste(f, (dx, dy), f)
        aligned.append(c)

    # Step 2: Find common bounding box across all aligned frames
    # (minimum x,y and maximum x,y that is non-transparent in ALL frames)
    fw = aligned[0].width
    fh = aligned[0].height
    min_x = fw; max_x = 0; min_y = fh; max_y = 0
    for f in aligned:
        for y in range(fh):
            for x in range(fw):
                if f.getpixel((x, y))[3] > 10:
                    min_x = min(min_x, x); max_x = max(max_x, x)
                    min_y = min(min_y, y); max_y = max(max_y, y)

    # Add padding
    pad = 3
    min_x = max(0, min_x - pad)
    min_y = max(0, min_y - pad)
    max_x = min(fw - 1, max_x + pad)
    max_y = min(fh - 1, max_y + pad)
    cw = max_x - min_x + 1
    ch = max_y - min_y + 1

    # Step 3: Crop all frames to common bounding box
    cropped = []
    for f in aligned:
        c = f.crop((min_x, min_y, max_x + 1, max_y + 1))
        cropped.append(c)

    # Step 4: Scale uniformly to target frame size
    scale = min(frame_size / cw, frame_size / ch)
    uw = max(1, int(cw * scale))
    uh = max(1, int(ch * scale))

    results = []
    for f in cropped:
        r = f.resize((uw, uh), Image.LANCZOS)
        c = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        c.paste(r, ((frame_size - uw) // 2, (frame_size - uh) // 2), r)
        # Final cleanup: pixels with very low alpha (resize artifacts) → fully transparent
        pixels = c.load()
        for y in range(frame_size):
            for x in range(frame_size):
                if pixels[x, y][3] < 20:
                    pixels[x, y] = (0, 0, 0, 0)
        results.append(c)

    strip = Image.new("RGBA", (frame_size * len(results), frame_size), (0, 0, 0, 0))
    for i, f in enumerate(results):
        strip.paste(f, (i * frame_size, 0), f)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    strip.save(str(out), format="PNG")
    n = len(results)
    print(f"  ✅ Strip: {out} ({frame_size*n}×{frame_size}, {n} frames, {os.path.getsize(output_path)//1024}KB)")
    return str(out)


def make_preset_runner(
    style: str = "boy", output_path: str = "",
    frame_size: int = DEFAULT_FRAME_SIZE, timeout: int = 180,
) -> str:
    """Generate a grid sprite from preset and process into strip (one shot)."""
    if style not in SPRITE_PRESETS:
        raise ValueError(f"Unknown style '{style}'. Available: {', '.join(SPRITE_PRESETS)}")
    if not output_path:
        # Use style-specific path to avoid overwriting other presets
        _preset_path(style).parent.mkdir(parents=True, exist_ok=True)
        output_path = str(_preset_path(style))

    preset = SPRITE_PRESETS[style]
    prompt = _build_grid_prompt(preset["char"], preset["anim_type"])
    print(f"  🎨 Generating {SPRITE_PRESETS[style]['name']} sprite...")

    # Generate 3x3 grid (temp file, cleaned up after)
    grid_path = str(Path(output_path).with_suffix("")) + f"_{style}_grid.png"
    generate_sprite(prompt, grid_path, timeout)
    result = process_grid_sprite(grid_path, output_path, frame_size=frame_size)
    if os.path.exists(grid_path):
        os.remove(grid_path)
    # Generate sprite preview HTML alongside the strip
    generate_sprite_preview(result, style)
    return result


def get_runner_path(episode_dir: str, style: str = "dino") -> str:
    """Resolve sprite path: episode-local > default asset, by style name."""
    local = _episode_path(episode_dir, style)
    if local.exists():
        return str(local)
    preset = _preset_path(style)
    if preset.exists():
        return str(preset)
    # Fallback: legacy runner.png
    legacy = Path(episode_dir) / SPRITES_DIR_NAME / SPRITE_FILE_NAME
    if legacy.exists():
        return str(legacy)
    return str(_preset_path("dino"))  # ultimate fallback


def generate_sprite_preview(strip_path: str, style: str = "") -> str:
    """Generate a standalone HTML preview of the 9-frame sprite animation.
    Saved alongside the strip as 'sprite-preview.html'."""
    import base64
    strip = Path(strip_path)
    if not strip.exists():
        return ""
    b64 = base64.b64encode(strip.read_bytes()).decode("ascii")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>精灵预览</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:sans-serif;background:#1a1a2e;color:#fff;padding:40px;}}
h1{{font-size:24px;margin-bottom:8px;}}
p{{color:rgba(255,255,255,.4);margin-bottom:24px;}}
.grid{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:32px;}}
.f{{text-align:center;}}
.f canvas{{width:80px;height:80px;image-rendering:pixelated;background:#333;border-radius:4px;}}
.f .n{{font-size:11px;color:rgba(255,255,255,.4);margin-top:4px;font-family:monospace;}}
.demo{{display:flex;gap:30px;align-items:flex-start;flex-wrap:wrap;}}
.demo canvas{{image-rendering:pixelated;background:#333;border-radius:8px;}}
.ctrl{{display:flex;gap:8px;align-items:center;margin-top:12px;flex-wrap:wrap;}}
.ctrl button{{padding:6px 16px;border:none;border-radius:4px;cursor:pointer;background:#FB7299;color:#fff;font-size:13px;}}
.ctrl span{{color:rgba(255,255,255,.5);font-size:13px;}}
</style>
</head><body>
<h1>🔍 精灵预览</h1>
<p>9帧网格 + 动画循环</p>
<div class="grid" id="grid"></div>
<div class="demo">
<canvas id="anim" width="200" height="200"></canvas>
<div class="ctrl">
<button onclick="{'' if 1 else ''}(function(){{let p=document.getElementById('playBtn');p.textContent=p.textContent=='⏸'?'▶':'⏸';window._ap=!window._ap;}})()" id="playBtn">⏸</button>
<span id="fps">1.2s 周期</span>
</div>
</div>
<script>
(function(){{
var src='data:image/png;base64,{b64}',FW=60,FH=60,N=9;
var img=new Image();img.onload=function(){{
var frames=[];
for(var i=0;i<N;i++){{var c=document.createElement('canvas');c.width=FW;c.height=FH;
c.getContext('2d').drawImage(img,i*FW,0,FW,FH,0,0,FW,FH);frames.push(c);
var d=document.createElement('div');d.className='f';
var cc=document.createElement('canvas');cc.width=FW;cc.height=FH;
cc.getContext('2d').drawImage(frames[i],0,0);
var lb=document.createElement('div');lb.className='n';
d.appendChild(cc);
document.getElementById('grid').appendChild(d);
}}
var ac=document.getElementById('anim').getContext('2d');
var cur=0;window._ap=true;
var cycle=1.2,frameDur=cycle/9,accum=0,last=0;
function draw(f){{ac.fillStyle='#333';ac.fillRect(0,0,200,200);
ac.save();ac.translate(100,100);var s=200/FW*0.85;ac.scale(s,s);
ac.drawImage(frames[Math.floor(f)%9],-FW/2,-FH/2);ac.restore();}}
function anim(t){{var dt=last?(t-last)/1000:0;last=t;
if(window._ap&&dt<0.1){{accum+=dt;if(accum>=frameDur){{cur=(cur+1)%9;accum-=frameDur;}}}}
draw(cur);requestAnimationFrame(anim);}}
requestAnimationFrame(anim);
}};img.src=src;
}})();
</script></body></html>"""
    preview_path = str(strip.with_name("sprite-preview.html"))
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  🔗 Sprite preview: {preview_path}")
    return preview_path


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="Sprite runner generator")
    sub = p.add_subparsers(dest="command", required=True)

    prs = sub.add_parser("preset", help="Generate sprite from preset style")
    prs.add_argument("--style", default="boy", choices=list(SPRITE_PRESETS.keys()))
    prs.add_argument("--out", default="")
    prs.add_argument("--frame-size", type=int, default=DEFAULT_FRAME_SIZE)
    prs.add_argument("--timeout", type=int, default=180)

    gen = sub.add_parser("generate", help="Generate 3x3 sprite grid")
    gen.add_argument("--prompt", default="")
    gen.add_argument("--out", default="")
    gen.add_argument("--timeout", type=int, default=180)

    proc = sub.add_parser("process", help="Process grid into strip")
    proc.add_argument("--in", dest="input", required=True)
    proc.add_argument("--out", required=True)
    proc.add_argument("--frame-size", type=int, default=DEFAULT_FRAME_SIZE)

    args = p.parse_args()

    if args.command == "preset":
        make_preset_runner(args.style, args.out, args.frame_size, args.timeout)
    elif args.command == "generate":
        generate_sprite(args.prompt, args.out, args.timeout)
    elif args.command == "process":
        process_grid_sprite(args.input, args.out, frame_size=args.frame_size)


if __name__ == "__main__":
    main()
