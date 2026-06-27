"""
v3/sprite_runner.py — Progress bar running character (sprite sheet)

Generates a 3x3 grid sprite sheet via AI, processes it into a horizontal strip
for the video progress bar running animation.

Usage:
    # Generate from a preset style
    python3 -m v3.sprite_runner preset --style boy --out v3/assets/sprite_runner.png

    # Process existing grid into strip
    python3 -m v3.sprite_runner process --in grid.png --out strip.png
"""
import argparse, os
from pathlib import Path

from PIL import Image

from v3.config import V3_DIR
from v3.imagegen import _wuyinkeji_generate

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
            "A precise 3x3 sprite sheet of ONE cute chibi boy running animation, "
            "side view, game sprite pixel art style, white background. "
            "Exact same character design in all 9 cells. "
            "Row 1 (left to right): left foot forward landing, "
            "both feet together under body, right foot pushing forward. "
            "Row 2 (left to right): right foot landing forward, "
            "both feet off ground in airborne stride, left foot swinging forward. "
            "Row 3 (left to right): left foot landing forward, "
            "both feet together mid-stride, right foot striding ahead. "
            "Simple flat vector art, minimal detail, clear leg positions showing running motion."
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

    # Step 1: Extract + remove bg + crop per frame
    raw_frames = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            frame = img.crop((col * fw, row * fh, (col + 1) * fw, (row + 1) * fh))
            bg = _detect_background(frame)
            cleaned = _remove_background(frame, bg)
            cropped = _autocrop(cleaned, padding=3)
            raw_frames.append(cropped)

    # Step 2: Find max content dimensions across all frames
    max_w = max(f.width for f in raw_frames)
    max_h = max(f.height for f in raw_frames)

    # Step 3: Pad each frame to MAX size (no cropping, all content preserved)
    # Center each frame's content on a uniform canvas of (max_w, max_h).
    # All frames end up the same size with their content positioned
    # consistently regardless of individual frame sizes.
    padded = []
    for f in raw_frames:
        c = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        c.paste(f, ((max_w - f.width) // 2, (max_h - f.height) // 2), f)
        padded.append(c)

    # Step 4: Scale uniformly to target size
    scale = min(frame_size / max_w, frame_size / max_h)
    fw_u, fh_u = max(1, int(max_w * scale)), max(1, int(max_h * scale))

    results = []
    for f in padded:
        r = f.resize((fw_u, fh_u), Image.LANCZOS)
        c = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        c.paste(r, ((frame_size - fw_u) // 2, (frame_size - fh_u) // 2), r)
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
