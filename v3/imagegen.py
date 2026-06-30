"""
v3/imagegen.py — Three-tier image generator

Fallback chain: wuyinkeji → pexels → pixabay → svg
"""
import os, sys, time, base64, io, json, re
from pathlib import Path
from v3.config import (
    WUYINKEJI_KEY, WUYINKEJI_SUBMIT_URL, WUYINKEJI_DETAIL_URL,
    PEXELS_KEY, PIXABAY_KEY,
    IMAGE_FALLBACK_CHAIN, VIDEO_WIDTH, VIDEO_HEIGHT, WUYINKEJI_SIZE_MAP, IMAGE_JPEG_QUALITY, IMAGE_PNG_COMPRESSION,
)

try:
    import requests
except ImportError:
    requests = None


# ══════════════════════════════════════════════════════════════════
# Tier 1: wuyinkeji (AI async generation)
# ══════════════════════════════════════════════════════════════════

def _wuyinkeji_generate(prompt: str, size: str = "16:9", timeout: int = 180) -> bytes:
    """Generate image via wuyinkeji async API. Returns image bytes."""
    if not requests:
        raise RuntimeError("requests not installed")
    api_size = WUYINKEJI_SIZE_MAP.get(size, "16:9")

    # Submit
    r = requests.post(WUYINKEJI_SUBMIT_URL, json={
        "prompt": prompt,
        "size": api_size,
        "key": WUYINKEJI_KEY,
    }, timeout=15)
    data = r.json()
    if data.get("code") != 200:
        raise RuntimeError(f"wuyinkeji submit failed: {data.get('msg', '?')}")
    task_id = data["data"]["id"]

    # Poll with exponential backoff
    wait = 3
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(wait)
        r = requests.get(WUYINKEJI_DETAIL_URL, params={
            "key": WUYINKEJI_KEY,
            "id": task_id,
        }, timeout=15)
        resp = r.json()
        if resp.get("code") != 200:
            wait = min(wait * 1.5, 30)
            continue
        status = resp.get("data", {}).get("status", 0)
        if status == 2:
            urls = resp.get("data", {}).get("result", [])
            if urls:
                img_r = requests.get(urls[0], timeout=60)
                return img_r.content
            raise RuntimeError("wuyinkeji: no result URL returned")
        elif status == -1:
            raise RuntimeError("wuyinkeji: content rejected (status=-1)")
        wait = min(wait * 1.5, 30)
    raise TimeoutError(f"wuyinkeji: timeout after {timeout}s")


# ══════════════════════════════════════════════════════════════════
# Tier 2: Pexels (real photo search)
# ══════════════════════════════════════════════════════════════════

def _pexels_search(prompt: str, orient: str = "landscape") -> bytes:
    """Search Pexels for a matching image, download first result."""
    if not requests:
        raise RuntimeError("requests not installed")
    keywords = re.sub(r"\([^)]*\)", "", prompt).strip()[:100]
    r = requests.get("https://api.pexels.com/v1/search", params={
        "query": keywords, "per_page": 5, "orientation": orient,
    }, headers={"Authorization": PEXELS_KEY}, timeout=15)
    data = r.json()
    photos = data.get("photos", [])
    if not photos:
        raise RuntimeError(f"Pexels: no results for '{keywords}'")
    candidates = []
    for p in photos:
        src = p.get("src", {})
        for key in ["large2x", "large", "medium"]:
            url = src.get(key)
            if url:
                candidates.append((url, p.get("width", 0)))
                break
    if not candidates:
        raise RuntimeError("Pexels: no valid image URLs")
    candidates.sort(key=lambda x: -x[1])
    img_r = requests.get(candidates[0][0], timeout=30)
    return img_r.content


# ══════════════════════════════════════════════════════════════════
# Tier 3: Pixabay (real photo search, fallback)
# ══════════════════════════════════════════════════════════════════

def _pixabay_search(prompt: str, orient: str = "horizontal") -> bytes:
    """Search Pixabay for a matching image, download first result."""
    if not requests:
        raise RuntimeError("requests not installed")
    keywords = re.sub(r"\([^)]*\)", "", prompt).strip()[:100]
    r = requests.get("https://pixabay.com/api/", params={
        "key": PIXABAY_KEY, "q": keywords,
        "image_type": "photo", "orientation": orient,
        "per_page": 5, "safesearch": "true",
    }, timeout=15)
    data = r.json()
    hits = data.get("hits", [])
    if not hits:
        raise RuntimeError(f"Pixabay: no results for '{keywords}'")
    hits.sort(key=lambda x: -(x.get("imageWidth", 0) or 0))
    url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
    if not url:
        raise RuntimeError("Pixabay: no valid image URL")
    img_r = requests.get(url, timeout=30)
    return img_r.content


# ══════════════════════════════════════════════════════════════════
# Tier 4: SVG fallback (always succeeds, instant)
# ══════════════════════════════════════════════════════════════════

def _svg_fallback(prompt: str, accent: str = "#cc785c",
                  canvas: str = "#faf9f5", size: tuple = (420, 380)) -> bytes:
    """Generate a stylish SVG placeholder with themed colors."""
    w, h = size
    title = prompt[:40] if prompt else "Illustration"
    svg = f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="{canvas}" rx="12"/>
  <circle cx="{w//2}" cy="{h//2 - 20}" r="50" fill="{accent}" opacity="0.12"/>
  <circle cx="{w//2}" cy="{h//2 - 20}" r="30" fill="{accent}" opacity="0.20"/>
  <text x="{w//2}" y="{h - 50}" text-anchor="middle" fill="{accent}"
        font-family="sans-serif" font-size="14" opacity="0.5">{title}</text>
</svg>'''
    return svg.encode("utf-8")


# ══════════════════════════════════════════════════════════════════
# Unified API
# ══════════════════════════════════════════════════════════════════

def generate_image(prompt: str, accent_color: str = "#cc785c",
                   canvas_color: str = "#faf9f5",
                   size: str = "16:9",
                   fallback_chain: list[str] | None = None) -> tuple[bytes, str]:
    """
    Generate an image using the fallback chain.
    Returns (image_bytes, source_name).
    """
    if fallback_chain is None:
        fallback_chain = IMAGE_FALLBACK_CHAIN

    last_error = None
    for source in fallback_chain:
        try:
            if source == "wuyinkeji":
                data = _wuyinkeji_generate(prompt, size)
            elif source == "pexels":
                data = _pexels_search(prompt)
            elif source == "pixabay":
                data = _pixabay_search(prompt)
            elif source == "svg":
                data = _svg_fallback(prompt, accent_color, canvas_color)
            else:
                continue
            return data, source
        except Exception as e:
            last_error = e
            continue

    data = _svg_fallback(prompt, accent_color, canvas_color)
    return data, "svg"


def resize_for_video(img_bytes: bytes, target_w: int = VIDEO_WIDTH,
                     target_h: int = VIDEO_HEIGHT,
                     pad_color: str = "#faf9f5") -> bytes:
    """Resize and pad image to target video dimensions. Falls back to PIL for unsupported formats."""
    import subprocess, tempfile, io
    # SVG data: convert to visible raster image via PIL
    if img_bytes[:4] == b"<svg" or img_bytes[:5] == b"<?xml":
        from PIL import Image, ImageDraw, ImageFont
        svg_text = img_bytes.decode("utf-8")
        import re
        m = re.search(r'<text[^>]*>(.*?)</text>', svg_text)
        title = m.group(1) if m else ""
        rgb = tuple(int(pad_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        # Create a visually distinct fallback image with gradient-like effect
        img = Image.new("RGB", (target_w, target_h), rgb)
        draw = ImageDraw.Draw(img)
        cx, cy = target_w // 2, target_h // 2
        accent_rgb = (79, 195, 161)
        # Large background shapes for visibility
        for r, a in [(400, 30), (280, 50), (160, 80)]:
            c = tuple(min(255, int(accent_rgb[i] * (a/100) + rgb[i] * (1 - a/100))) for i in range(3))
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=c)
        # Decorative circles
        for r, a in [(500, 15), (350, 25), (200, 40), (120, 60)]:
            c = tuple(min(255, int(accent_rgb[i] * (a/100) + rgb[i] * (1 - a/100))) for i in range(3))
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c, width=3)
        # Horizontal line decoration
        draw.rectangle([100, cy-1, target_w-100, cy+1], fill=accent_rgb)
        if title:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
            except:
                font = None
                font_small = None
            bbox = draw.textbbox((0, 0), title, font=font)
            tw = bbox[2] - bbox[0]
            # Title text
            draw.text(((target_w - tw) // 2, target_h - 180), title, fill=(200, 220, 230), font=font)
            # Subtitle
            subtitle = "AI Generated Illustration"
            bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            draw.text(((target_w - tw2) // 2, target_h - 120), subtitle, fill=(107, 125, 143), font=font_small)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_bytes = buf.getvalue()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_in:
        tmp_in.write(img_bytes)
        in_path = tmp_in.name
    out_path = in_path + "_out.jpg"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", in_path,
            "-vf", f"scale='min({target_w},iw)':'min({target_h},ih)':force_original_aspect_ratio=decrease,"
                   f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color={pad_color}",
            "-q:v", str(IMAGE_JPEG_QUALITY), out_path
        ], capture_output=True, timeout=30, check=True)
        with open(out_path, "rb") as f:
            return f.read()
    except Exception as e:
        # If ffmpeg fails (e.g. unsupported format), fall back to PIL
        from PIL import Image as PILImage
        try:
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            pil_img = pil_img.convert("RGB")
            pil_img.thumbnail((target_w, target_h), PILImage.LANCZOS)
            new_img = PILImage.new("RGB", (target_w, target_h), tuple(int(pad_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)))
            offset = ((target_w - pil_img.width) // 2, (target_h - pil_img.height) // 2)
            new_img.paste(pil_img, offset)
            buf = io.BytesIO()
            new_img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except:
            raise
    finally:
        for p in [in_path, out_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


def image_to_b64(img_bytes: bytes, mime: str = "image/jpeg") -> str:
    """Convert image bytes to base64 data URI."""
    b64 = base64.b64encode(img_bytes).decode()
    return f"data:{mime};base64,{b64}"


def generate_all_images(slots: list[dict], output_dir: str,
                        design: dict | None = None) -> dict[str, str]:
    """
    Given a list of image_slots (from T2), generate all missing images.
    Returns dict of {filename: base64_data_uri}.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    accent = (design or {}).get("colors", {}).get("primary", "#cc785c")
    canvas = (design or {}).get("colors", {}).get("canvas", "#faf9f5")
    design_name = (design or {}).get("name", "")
    style_hints = {
        "bilibili": "anime aesthetic, cel shading style, vibrant colors, soft gradients, studio ghibli inspired, expressive eyes, dreamy atmosphere, japanese animation style, radiant lighting",
        "talk-show": "cartoon illustration, comic book style, expressive, flat vector art, bold colors, exaggerated expressions",
        "claude": "warm illustration, painterly style, soft edges, digital art",
        "dark-teal": "cyberpunk style, neon accents, dark background, digital art",
        "linear": "minimalist vector art, clean lines, geometric shapes, modern illustration",
        "mintlify": "clean vector illustration, flat design, professional, modern",
        "stripe": "clean vector art, isometric style, professional illustration",
        "vercel": "minimalist vector art, clean lines, modern illustration, simple shapes",
    }
    default_hint = style_hints.get(design_name, "digital art, illustration, clear, professional")
    style_prefix = f"{default_hint}. The image should be visually clear for a video presentation."


    results = {}
    existing = set()
    for f in out.glob("*"):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            existing.add(f.name)

    for slot in slots:
        fn = slot.get("filename", "")
        if not fn:
            continue
        if fn in existing:
            with open(out / fn, "rb") as f:
                data = f.read()
            results[fn] = image_to_b64(resize_for_video(data, pad_color=canvas))
            continue

        prompt = slot.get("prompt") or slot.get("content", "")
        size = slot.get("size", "16:9")
        print(f"  🖼  Generating {fn} ({slot.get('slot','?')})...", end=" ", flush=True)

        # Apply style prefix to prompt based on design
        styled_prompt = f"{prompt.strip()}. {style_prefix}"
        if design_name in ("bilibili", "talk-show"):
            styled_prompt = f"[{default_hint}] {prompt.strip()}"

        img_data, source = generate_image(styled_prompt, accent, canvas, size)

        img_data = resize_for_video(img_data, pad_color=canvas)

        with open(out / fn, "wb") as f:
            f.write(img_data)
        print(f"✓ ({source}, {len(img_data)//1024}KB)")

        results[fn] = image_to_b64(img_data)

    return results


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "A cute robot teaching AI concepts, digital art style"
    data, source = generate_image(prompt)
    print(f"Source: {source}, size: {len(data)} bytes")
    out = "/tmp/test_gen.jpg"
    with open(out, "wb") as f:
        f.write(data)
    print(f"Saved to {out}")
