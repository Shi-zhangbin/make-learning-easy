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
ASSET_PATH = Path(V3_DIR) / "assets" / "sprite_runner.png"
SPRITES_DIR_NAME = "sprites"
SPRITE_FILE_NAME = "runner.png"

# ── Animation cycle templates (shared quality rules + 9-frame descriptions) ──
# Each template enforces: identical character, no bounce, smooth loop, white bg
ANIMATION_CYCLES = {
    "run": (
        "9-frame running cycle loop, contact→support→pass→reach pattern repeated:\n"
        "Cell 1: left foot landing forward on ground, right leg trailing back.\n"
        "Cell 2: left foot flat on ground, body over foot, right leg behind.\n"
        "Cell 3: both legs passing under body at midpoint.\n"
        "Cell 4: right leg reaching forward, left leg pushing behind.\n"
        "Cell 5: right foot landing forward on ground, left leg trailing.\n"
        "Cell 6: right foot flat, body over foot, left leg behind.\n"
        "Cell 7: both legs passing under body again.\n"
        "Cell 8: left leg reaching forward, right leg pushing behind.\n"
        "Cell 9: left leg reaching forward, still in the air about to land — "
        "DIFFERENT from cell 1 which has already landed. "
        "The loop: cell 9 (mid-reach) → cell 1 (just landed) is seamless."
    ),
    "walk": (
        "9-frame walking cycle loop, slower than running, gentle transitions:\n"
        "Cell 1: left foot stepping forward, heel touching ground.\n"
        "Cell 2: left foot flat on ground, body centered, right foot behind.\n"
        "Cell 3: both feet passing under body, casual pace.\n"
        "Cell 4: right foot stepping forward, heel touching.\n"
        "Cell 5: right foot flat, body centered, left foot behind.\n"
        "Cell 6: both feet passing again.\n"
        "Cell 7: left foot starting to step forward.\n"
        "Cell 8: left foot reaching forward.\n"
        "Cell 9: left foot about to touch ground — seamless to cell 1."
    ),
    "jump": (
        "9-frame jumping/hopping forward cycle loop:\n"
        "Cell 1: standing upright, legs together, preparing to jump.\n"
        "Cell 2: crouching down, knees bent, arms back.\n"
        "Cell 3: springing upward, arms rising, legs extending.\n"
        "Cell 4: fully airborne, legs tucked under body.\n"
        "Cell 5: reaching peak height, body extended.\n"
        "Cell 6: starting descent, legs extending downward.\n"
        "Cell 7: landing on both feet, knees bending to absorb.\n"
        "Cell 8: crouched after landing, recovering balance.\n"
        "Cell 9: rising back to standing — seamless to cell 1."
    ),
    "cycle": (
        "9-frame bicycle riding cycle loop:\n"
        "Cell 1: left pedal starting to push down from highest point.\n"
        "Cell 2: left pedal going down, right pedal coming up.\n"
        "Cell 3: both pedals at middle height crossing.\n"
        "Cell 4: right pedal at highest point pushing down.\n"
        "Cell 5: right pedal going down, left pedal coming up.\n"
        "Cell 6: both pedals crossing at middle again.\n"
        "Cell 7: left pedal near highest point, starting to push.\n"
        "Cell 8: left pedal starting its downward stroke.\n"
        "Cell 9: left pedal partway down, continuing stroke — flows into cell 1.\n"
        "Cell 9 and cell 1 are DIFFERENT phases of the pedal stroke, not the same."
    ),
    "skateboard": (
        "9-frame skateboarding cycle loop, smooth rolling:\n"
        "Cell 1: standing centered on board, cruising forward.\n"
        "Cell 2: slight crouch, left foot pushing off ground.\n"
        "Cell 3: left foot off ground, both on board gliding.\n"
        "Cell 4: standing tall, arms out for balance.\n"
        "Cell 5: slight crouch, right foot pushing.\n"
        "Cell 6: both feet on board coasting.\n"
        "Cell 7: leaning forward, preparing next push.\n"
        "Cell 8: crouching slightly, shifting weight.\n"
        "Cell 9: weight centered, about to stand upright — leads into cell 1.\n"
        "Cell 9 is COMING INTO the cruising pose, cell 1 IS cruising. Different."
    ),
    "moonwalk": (
        "9-frame moonwalk (gliding backward) cycle loop:\n"
        "Cell 1: standing upright, feet together.\n"
        "Cell 2: left foot sliding backward flat on ground.\n"
        "Cell 3: left foot continues sliding, right heel lifts.\n"
        "Cell 4: right foot sliding back, left foot flat.\n"
        "Cell 5: both feet sliding back together.\n"
        "Cell 6: right foot slides back more, left heel lifts.\n"
        "Cell 7: left foot sliding back, right foot flat.\n"
        "Cell 8: both feet together sliding.\n"
        "Cell 9: feet together, about to start next cycle."
    ),
    "dance": (
        "9-frame dance groove cycle loop, stepping in place:\n"
        "Cell 1: arms up, stepping right foot out.\n"
        "Cell 2: swaying hips, arms down.\n"
        "Cell 3: twisting body, left arm up.\n"
        "Cell 4: spin move, arms extended.\n"
        "Cell 5: body wave, leaning back.\n"
        "Cell 6: side step, arms low.\n"
        "Cell 7: both arms up, knee up.\n"
        "Cell 8: stepping left, arms out.\n"
        "Cell 9: back to start pose — seamless to cell 1."
    ),
    "fly": (
        "9-frame superhero flying forward cycle loop:\n"
        "Cell 1: both arms forward, diving slightly.\n"
        "Cell 2: one arm forward, gliding level.\n"
        "Cell 3: arms spread wide, soaring upward.\n"
        "Cell 4: both fists forward, speeding up.\n"
        "Cell 5: banking turn, one arm up.\n"
        "Cell 6: level flight cruising.\n"
        "Cell 7: diving again, arms close to body.\n"
        "Cell 8: pulling up, arms wide.\n"
        "Cell 9: preparing for next dive — seamless to cell 1."
    ),
}

# ── Shared prompt builder ──
_BASE_QUALITY = (
    "IDENTICAL character SIZE, POSITION, HEIGHT and APPEARANCE in ALL 9 cells. "
    "No vertical bouncing. Minimal frame-to-frame change for smooth animation. "
    "Cell 9 should flow seamlessly into cell 1 when animation loops. "
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
    "dino":   {"name": "小恐龙",  "desc": "Cute blue dinosaur running",    "anim_type": "run",        "char": "cute baby blue dinosaur with tiny arms, big head, visible tail"},
    "walk":   {"name": "散步",    "desc": "Cute chibi boy walking casually","anim_type": "walk",       "char": "cute chibi boy"},
    "cycle":  {"name": "骑车",    "desc": "Cute chibi boy riding bicycle", "anim_type": "cycle",      "char": "cute chibi boy with small bicycle"},
    "skateboard": {"name": "滑板", "desc": "Cool chibi boy skateboarding", "anim_type": "skateboard", "char": "cool chibi boy with skateboard"},
    "jump":   {"name": "跳跃",    "desc": "Bouncy chibi boy jumping",      "anim_type": "jump",       "char": "cute chibi boy"},
    "moonwalk": {"name": "太空步","desc": "Funny chibi moonwalking",       "anim_type": "moonwalk",   "char": "cool chibi boy with confident expression"},
    "dance":  {"name": "跳舞",    "desc": "Groovy chibi boy dancing",      "anim_type": "dance",      "char": "fun energetic chibi boy"},
    "fly":    {"name": "飞翔",    "desc": "Superhero chibi boy flying",    "anim_type": "fly",        "char": "cute chibi boy superhero with flowing cape"},
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
        output_path = str(ASSET_PATH)

    preset = SPRITE_PRESETS[style]
    prompt = _build_grid_prompt(preset["char"], preset["anim_type"])
    print(f"  🎨 Generating {SPRITE_PRESETS[style]['name']} sprite...")

    # Generate 3x3 grid (temp file, cleaned up after)
    grid_path = str(Path(output_path).with_suffix("")) + f"_{style}_grid.png"
    generate_sprite(prompt, grid_path, timeout)
    result = process_grid_sprite(grid_path, output_path, frame_size=frame_size)
    if os.path.exists(grid_path):
        os.remove(grid_path)
    return result


def get_runner_path(episode_dir: str) -> str:
    """Resolve sprite path: episode-local > default asset."""
    local = Path(episode_dir) / SPRITES_DIR_NAME / SPRITE_FILE_NAME
    return str(local) if local.exists() else str(ASSET_PATH)


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
