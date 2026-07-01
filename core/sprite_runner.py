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

# ── Sprite Presets ──
# Uses grid prompts: a single 3x3 image with specific per-cell descriptions.
# One AI call = consistent character across all 9 frames.
SPRITE_PRESETS = {
    "boy": {
        "name": "小男孩",
        "desc": "Cute chibi boy running",
        "grid_prompt": (
            "A 3x3 sprite sheet, 9 cells, ONE cute chibi boy "
            "side-view running animation, pixel art, white background. "
            "IDENTICAL character size, position and height in ALL cells. "
            "No bouncing. 9-frame running cycle:\n"
            "Cell 1: both legs slightly bent, body upright, neutral standing pose.\n"
            "Cell 2: left leg stepping forward, right leg behind.\n"
            "Cell 3: both legs passing under body at midpoint.\n"
            "Cell 4: right leg reaching forward, left leg pushing off.\n"
            "Cell 5: both legs passing again at midpoint.\n"
            "Cell 6: left leg striding wide forward, right leg trailing.\n"
            "Cell 7: right leg pushing forward, body leaning forward more.\n"
            "Cell 8: both legs wider apart, accelerating stride.\n"
            "Cell 9: maximum forward lean, longest stride, sprint pose — "
            "completely different from cell 1 (standing).\n"
            "Minimal angle change per cell. Flat vector, thick outlines."
        ),
    },
    "dino": {
        "name": "小恐龙",
        "desc": "Cute blue dinosaur running",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute baby blue dinosaur running animation, "
            "side view, game sprite style, pixel art, white background. "
            "Exactly the same dinosaur design in all 9 cells. "
            "Chubby cute dinosaur with tiny arms, big head, tail visible in every cell. "
            "Row 1 (left to right): left foot forward landing, "
            "both feet together body compressed, right foot pushing forward. "
            "Row 2: right foot landing forward, small airborne hop, "
            "left foot swinging forward. "
            "Row 3: left foot landing forward, both together, "
            "right foot striding ahead. "
            "Simple flat vector art, clear running motion, identical character size in every cell."
        ),
    },
    "walk": {
        "name": "散步",
        "desc": "Cute chibi boy walking casually",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute chibi boy walking animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character design in all 9 cells, same as running boy but slower pace. "
            "Row 1 (left to right): left foot stepping forward lazily, "
            "both feet flat on ground in mid-stride, right foot beginning to lift. "
            "Row 2 (left to right): right foot stepping forward, "
            "both feet together brief pause, left foot starting forward. "
            "Row 3 (left to right): left foot landing forward, "
            "both feet momentarily together, right foot dragging forward. "
            "Relaxed posture, arms swinging casually, simple flat vector art."
        ),
    },
    "cycle": {
        "name": "骑车",
        "desc": "Cute chibi boy riding a bicycle",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute chibi boy riding a bicycle animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character and bicycle design in all 9 cells. "
            "Row 1 (left to right): left pedal down pushing, "
            "both pedals horizontal mid-rotation, right pedal pushing down. "
            "Row 2 (left to right): right pedal down, "
            "both pedals level cruising, left foot pushing down. "
            "Row 3 (left to right): left pedal down, "
            "pedals level smooth rotation, right pedal starting down. "
            "Small bicycle with visible wheels and pedal rotation, simple flat vector art."
        ),
    },
    "skateboard": {
        "name": "滑板",
        "desc": "Cool chibi boy skateboarding",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cool chibi boy skateboarding animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character and skateboard design in all 9 cells. "
            "Row 1 (left to right): crouched low pushing off with left foot, "
            "both feet on board gliding, right foot dragging to brake. "
            "Row 2 (left to right): standing tall cruising, "
            "slight crouch absorbing bump, leaning forward accelerating. "
            "Row 3 (left to right): pushing off with right foot, "
            "both feet on board coasting, landing after small ollie. "
            "Skateboard with visible wheels, relaxed cool posture, flat vector art."
        ),
    },
    "jump": {
        "name": "跳跃",
        "desc": "Bouncy chibi boy jumping/hopping forward",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute chibi boy hopping forward animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character design in all 9 cells. "
            "Row 1 (left to right): crouching down arms back preparing to jump, "
            "springing upward arms rising, fully airborne legs tucked. "
            "Row 2 (left to right): mid-air reaching peak height, "
            "starting descent legs extending, landing on both feet crouching. "
            "Row 3 (left to right): bouncing up again arms up, "
            "full airborne star jump, landing softly bending knees. "
            "Expressive jumping motion, happy expression, simple flat vector art."
        ),
    },
    "moonwalk": {
        "name": "太空步",
        "desc": "Funny chibi moonwalking backward",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute chibi boy moonwalking animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character design in all 9 cells. "
            "Row 1 (left to right): gliding backward left foot flat, "
            "right foot sliding back heel down, left foot pulling back. "
            "Row 2 (left to right): both feet sliding back smoothly, "
            "right foot flat gliding, left foot sliding back toe. "
            "Row 3 (left to right): left foot flat sliding back, "
            "both feet gliding together, right foot toe slide. "
            "Cool confident expression, Michael Jackson style, flat vector art."
        ),
    },
    "dance": {
        "name": "跳舞",
        "desc": "Groovy chibi boy dancing in place while moving forward",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute chibi boy dancing animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character design in all 9 cells. "
            "Row 1 (left to right): arms up grooving left foot out, "
            "both arms down swaying hips, right arm up pointing. "
            "Row 2 (left to right): twisting body left arms out, "
            "spin move arms wide, body wave leaning back. "
            "Row 3 (left to right): stepping side to side arms low, "
            "both arms up cheering, groove pose knee up. "
            "Fun energetic dancing, star sunglasses, simple flat vector art."
        ),
    },
    "fly": {
        "name": "飞翔",
        "desc": "Superhero chibi boy flying forward",
        "grid_prompt": (
            "A precise 3x3 sprite sheet of ONE cute chibi boy superhero flying animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character design in all 9 cells, cape flowing. "
            "Row 1 (left to right): both arms forward diving down, "
            "one arm forward gliding level, cape billowing behind. "
            "Row 2 (left to right): arms spread wide soaring up, "
            "both fists forward speeding up, banking turn one arm up. "
            "Row 3 (left to right): diving again arms tucked, "
            "level flight cruising, pulling up arms wide. "
            "Superhero pose with flowing cape, determined expression, flat vector art."
        ),
    },
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

    prompt = SPRITE_PRESETS[style]["grid_prompt"]
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
