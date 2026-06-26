"""
v3/sprite_runner.py — Progress bar running character (sprite sheet)

Generates AI sprite sheets, processes grid→horizontal strip,
and manages the default runner asset for video progress bars.

Usage:
    # Generate a new 3x3 sprite sheet via wuyinkeji
    python3 -m v3.sprite_runner generate --prompt "..." --out grid.png

    # Process an existing grid into a horizontal strip
    python3 -m v3.sprite_runner process --in grid.png --out strip.png
"""
import argparse, os, sys, io
from pathlib import Path

from PIL import Image

from v3.config import V3_DIR, WUYINKEJI_SIZE_MAP
from v3.imagegen import _wuyinkeji_generate

# ── Constants ──
DEFAULT_FRAMES = 9          # 3×3 grid
DEFAULT_FRAME_SIZE = 60     # px, final sprite size
DEFAULT_PROMPT = (
    "A cute anime-style boy character running animation, "
    "sprite sheet with 3x3 grid showing a full running cycle from left to right, "
    "flat vector art, vibrant colors, clean lines on white background, "
    "game sprite style, 9 frames of continuous running motion, "
    "chibi proportions, simple design suitable for video progress bar"
)
ASSET_PATH = Path(V3_DIR) / "assets" / "sprite_runner.png"

# Episode-level sprites directory name
SPRITES_DIR_NAME = "sprites"
SPRITE_FILE_NAME = "runner.png"


# ══════════════════════════════════════════════════════════════════
# Grid processing
# ══════════════════════════════════════════════════════════════════

def process_grid_sprite(
    input_path: str,
    output_path: str,
    grid_cols: int = 3,
    grid_rows: int = 3,
    frame_size: int = DEFAULT_FRAME_SIZE,
) -> str:
    """Extract frames from a grid sprite sheet, crop to content, resize, and
    assemble into a horizontal strip.

    Args:
        input_path: Path to the grid sprite sheet (e.g. wuyinkeji output).
        output_path: Where to save the horizontal strip.
        grid_cols: Number of columns in the grid.
        grid_rows: Number of rows in the grid.
        frame_size: Target size in pixels (square).

    Returns:
        Path to the output file.
    """
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    fw, fh = w // grid_cols, h // grid_rows

    frames = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            frame = img.crop((col * fw, row * fh, (col + 1) * fw, (row + 1) * fh))
            # Auto-crop to content (remove surrounding blank pixels)
            frame = _autocrop(frame)
            frames.append(frame)

    # Determine uniform size: use the max bounding box across all frames
    max_w = max(f.width for f in frames)
    max_h = max(f.height for f in frames)
    # Scale uniformly so the largest dimension fits frame_size
    scale = min(frame_size / max_w, frame_size / max_h) if max_w and max_h else 1
    new_w = max(1, int(max_w * scale))
    new_h = max(1, int(max_h * scale))

    # Resize all frames to uniform size (centered on transparent canvas)
    uniform_frames = []
    for frame in frames:
        resized = frame.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        x = (frame_size - new_w) // 2
        y = (frame_size - new_h) // 2
        canvas.paste(resized, (x, y), resized)
        uniform_frames.append(canvas)

    # Assemble horizontally
    strip_w = frame_size * len(uniform_frames)
    strip = Image.new("RGBA", (strip_w, frame_size), (0, 0, 0, 0))
    for i, frame in enumerate(uniform_frames):
        strip.paste(frame, (i * frame_size, 0), frame)

    # Save as PNG (preserve transparency)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    strip.save(str(out), format="PNG")
    print(f"  ✅ Sprite strip: {out} ({strip_w}×{frame_size}, {len(uniform_frames)} frames)")
    return str(out)


def _autocrop(img: Image.Image, padding: int = 2) -> Image.Image:
    """Crop transparent borders from a PIL image."""
    bbox = img.getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        # Add small padding so the character isn't flush against edges
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(img.width, x1 + padding)
        y1 = min(img.height, y1 + padding)
        return img.crop((x0, y0, x1, y1))
    return img


# ══════════════════════════════════════════════════════════════════
# AI generation
# ══════════════════════════════════════════════════════════════════

def generate_sprite(
    prompt: str = DEFAULT_PROMPT,
    output_path: str = "",
    timeout: int = 180,
) -> str:
    """Generate a 3×3 sprite sheet via wuyinkeji API.

    Args:
        prompt: Image description for the AI.
        output_path: Where to save the raw grid image.
        timeout: Max wait in seconds.

    Returns:
        Path to the saved grid image.
    """
    if not output_path:
        output_path = str(Path.cwd() / "run_sprite_grid.png")

    print(f"  🎨 Generating sprite: '{prompt[:60]}...'")
    img_data = _wuyinkeji_generate(prompt, size="1:1", timeout=timeout)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        f.write(img_data)
    print(f"  ✅ Grid saved: {out} ({len(img_data)//1024}KB)")
    return str(out)


# ══════════════════════════════════════════════════════════════════
# Full pipeline: generate + process in one shot
# ══════════════════════════════════════════════════════════════════

def make_runner(
    prompt: str = DEFAULT_PROMPT,
    output_path: str = "",
    frame_size: int = DEFAULT_FRAME_SIZE,
    timeout: int = 180,
) -> str:
    """Generate a sprite sheet and process it into a horizontal strip.

    Args:
        prompt: Image description for AI generation.
        output_path: Where to save the final strip.
        frame_size: Target sprite size.
        timeout: Max wait for generation.

    Returns:
        Path to the final strip.
    """
    if not output_path:
        output_path = str(ASSET_PATH)

    # Generate grid
    grid_path = output_path.replace(".png", "_grid.png")
    generate_sprite(prompt, grid_path, timeout)

    # Process into strip
    strip_path = output_path
    process_grid_sprite(grid_path, strip_path, frame_size=frame_size)

    return strip_path


def get_runner_path(episode_dir: str) -> str:
    """Resolve the sprite runner path for an episode.

    Checks episode-local sprites/runner.png first, falls back to default asset.
    """
    local = Path(episode_dir) / SPRITES_DIR_NAME / SPRITE_FILE_NAME
    if local.exists():
        return str(local)
    # Fall back to default asset
    return str(ASSET_PATH)


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Sprite runner generator")
    sub = parser.add_subparsers(dest="command", required=True)

    # Generate command
    gen = sub.add_parser("generate", help="Generate 3×3 sprite grid via AI")
    gen.add_argument("--prompt", default=DEFAULT_PROMPT, help="Image description")
    gen.add_argument("--out", default="", help="Output path for grid PNG")
    gen.add_argument("--timeout", type=int, default=180, help="Max wait in seconds")

    # Process command
    proc = sub.add_parser("process", help="Process grid into horizontal strip")
    proc.add_argument("--in", dest="input", required=True, help="Input grid PNG")
    proc.add_argument("--out", required=True, help="Output strip PNG")
    proc.add_argument("--frame-size", type=int, default=DEFAULT_FRAME_SIZE, help="Target frame size")

    # Make command (generate + process)
    mk = sub.add_parser("make", help="Generate + process in one shot")
    mk.add_argument("--prompt", default=DEFAULT_PROMPT, help="Image description")
    mk.add_argument("--out", default="", help="Output strip path")
    mk.add_argument("--frame-size", type=int, default=DEFAULT_FRAME_SIZE)
    mk.add_argument("--timeout", type=int, default=180)

    args = parser.parse_args()

    if args.command == "generate":
        generate_sprite(args.prompt, args.out, args.timeout)
    elif args.command == "process":
        process_grid_sprite(args.input, args.out, frame_size=args.frame_size)
    elif args.command == "make":
        make_runner(args.prompt, args.out, args.frame_size, args.timeout)


if __name__ == "__main__":
    main()
