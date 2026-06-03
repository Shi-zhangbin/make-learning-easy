#!/usr/bin/env python3
"""
images_to_base64.py — 图片目录 → base64 映射 JSON

用法:
  python3 scripts/images_to_base64.py --dir 素材/ --out images_b64.json
  python3 scripts/images_to_base64.py --dir 素材/ --quality 85 --max-width 1280 --out images_b64.json
  python3 scripts/images_to_base64.py --dir 素材/ --html-script images_script.js
"""

import argparse, base64, json, os, sys
from pathlib import Path

try:
    from PIL import Image; HAS_PIL = True
except ImportError:
    HAS_PIL = False

EXTS = {".png",".jpg",".jpeg",".gif",".webp"}
MIME = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp"}

def compress(path, quality=85, mw=1920, mh=1080):
    if not HAS_PIL: return None
    img = Image.open(path)
    if img.mode in ("RGBA","P"): img = img.convert("RGB")
    w,h = img.size
    if w>mw or h>mh:
        r = min(mw/w, mh/h, 1.0)
        img = img.resize((int(w*r),int(h*r)), Image.LANCZOS)
    import io; buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()

def run(directory, quality=85, compress_flag=True, mw=1920, mh=1080, prefix="images"):
    dp = Path(directory)
    if not dp.is_dir():
        print(f"❌ 目录不存在: {dp}", file=sys.stderr)
        return {"images":{}, "summary":{"count":0,"total_bytes":0,"total_b64_bytes":0}}
    files = sorted([f for f in dp.iterdir() if f.suffix.lower() in EXTS])
    if not files:
        print("⚠️  无图片"); return {"images":{},"summary":{"count":0,"total_bytes":0,"total_b64_bytes":0}}
    images, orig_total, b64_total, comp_n, count = {}, 0, 0, 0, 0
    for fp in files:
        orig = fp.stat().st_size; orig_total += orig
        if compress_flag and HAS_PIL and fp.suffix.lower() in {".png",".jpg",".jpeg"}:
            comp = compress(str(fp), quality, mw, mh)
            if comp:
                b64 = base64.b64encode(comp).decode(); mime = "image/jpeg"
                if len(comp) < orig * 0.9: comp_n += 1
            else:
                b64 = base64.b64encode(fp.read_bytes()).decode(); mime = MIME.get(fp.suffix, "image/png")
        else:
            b64 = base64.b64encode(fp.read_bytes()).decode(); mime = MIME.get(fp.suffix, "image/png")
        uri = f"data:{mime};base64,{b64}"
        images[f"{prefix}/{fp.name}"] = uri
        b64_total += len(uri.encode()); count += 1
        print(f"  ✓ {fp.name:35s} {orig//1024:>5d}KB → b64 {len(b64)//1024:>5d}KB" + (" 💾" if comp_n else ""))
    return {"images":images,"summary":{"count":count,"total_bytes":orig_total,"total_b64_bytes":b64_total,"compressed":comp_n}}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", required=True); p.add_argument("--out", default="images_b64.json")
    p.add_argument("--quality", type=int, default=85); p.add_argument("--no-compress", action="store_true")
    p.add_argument("--max-width", type=int, default=1920); p.add_argument("--max-height", type=int, default=1080)
    p.add_argument("--prefix", default="images"); p.add_argument("--html-script")
    args = p.parse_args()
    r = run(args.dir, args.quality, not args.no_compress, args.max_width, args.max_height, args.prefix)
    if r["summary"]["count"] == 0: return
    with open(args.out, "w") as f: json.dump(r, f, ensure_ascii=False, indent=2)
    s = r["summary"]
    print(f"\n💾 {args.out}  |  {s['count']}张  |  原始{s['total_bytes']//1024:,}KB  |  b64{s['total_b64_bytes']//1024:,}KB")
    if args.html_script:
        script = "<script>window.__IMAGES=window.__IMAGES||{};\n"
        for k,v in r["images"].items():
            script += f'window.__IMAGES["{k}"]="{v}";\n'
        script += "</script>"
        with open(args.html_script, "w") as f: f.write(script)
        print(f"   HTML script: {args.html_script}")

if __name__ == "__main__":
    main()
