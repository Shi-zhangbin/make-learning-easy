#!/usr/bin/env python3
"""
render_compositions.py — 一键生成 composition（含图 + design tokens + standalone）

Hermes 执行 T6 时唯一允许的方式。
禁止手写 gen_compositions.py。

用法:
  python3 scripts/render_compositions.py <项目名>
  python3 scripts/render_compositions.py <项目名> --dry-run

流程:
  1. 读 timeline.json → 每页内容和时长
  2. 读 image_slots.json + images/ → base64 图片
  3. 用 composition_helper.py 生成标准 composition
  4. 写 index.html
  5. 验证 brand color + standalone
"""

import json, os, sys, base64, glob, re

BASE = os.path.expanduser("~/Desktop/ascend-pipeline")


def find_project(name):
    if os.path.isabs(name) and os.path.isdir(name):
        return os.path.abspath(name)
    for d in [os.path.join(BASE, "episodes", name), os.path.join(BASE, name)]:
        if os.path.isdir(d):
            return d
    return None


def find_file(project, name):
    for root, dirs, files in os.walk(project):
        if name in files:
            return os.path.join(root, name)
    return None


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_images(project):
    """Load all images from images/ directory as base64 dict."""
    img_dir = os.path.join(project, "images")
    images = {}
    if os.path.isdir(img_dir):
        for fname in os.listdir(img_dir):
            if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            fpath = os.path.join(img_dir, fname)
            ext = fname.split('.')[-1]
            mime = "image/png" if ext.lower() == "png" else "image/jpeg"
            with open(fpath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            images[fname] = {"mime": mime, "b64": b64, "size": os.path.getsize(fpath)}
    return images


def build_compositions(project, dry_run=False):
    """Main composition builder."""
    print(f"\n{'='*60}")
    print(f"render_compositions.py — {os.path.basename(project)}")
    print(f"{'='*60}")

    # 1. Load inputs
    tl_path = find_file(project, "timeline.json")
    slots_path = find_file(project, "image_slots.json")

    if not tl_path:
        print("❌ timeline.json not found. Run T2 first.")
        return False

    tl = load_json(tl_path)
    pages = tl.get("slides", tl.get("pages", []))

    slots = []
    if slots_path:
        slots_data = load_json(slots_path)
        slots = slots_data.get("slots", slots_data) if isinstance(slots_data, dict) else slots_data

    images = load_images(project)

    # 2. Import composition_helper
    helper_path = os.path.join(BASE, "scripts", "composition_helper.py")
    spec = importlib.util.spec_from_file_location("composition_helper", helper_path)
    ch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ch)

    comp_dir = os.path.join(project, "compositions")
    if not dry_run:
        os.makedirs(comp_dir, exist_ok=True)

    # 3. Generate each composition
    index_pages = []
    # Build slot lookup: filename -> slot data
    slot_map = {}
    for s in slots:
        fn = s.get("filename", "")
        if fn:
            slot_map[fn] = s
    
    print(f"\nPages: {len(pages)}")
    print(f"Image slots: {len(slots)}")
    print(f"Images loaded: {len(images)}")
    print(f"\nGenerating compositions...")

    for i, page in enumerate(pages):
        sid = page.get("id", f"s{i+1}")
        dur = page.get("duration", 10)
        title = page.get("label", page.get("slide_title", f"Page {i+1}"))
        narration = page.get("narration", page.get("narration_text", ""))
        layout = page.get("layout", "concept")
        start = page.get("start", 0)

        # Find matching image
        img_html = ""
        for fn, img_data in images.items():
            # Match by page number in filename
            page_num = re.search(r'(\d+)', sid)
            fn_num = re.search(r'(\d+)', fn)
            if page_num and fn_num and page_num.group(1) == fn_num.group(1):
                img_html = f'<div class="hf-animate-2" style="position:absolute;top:60px;right:60px;width:280px"><img src="data:{img_data["mime"]};base64,{img_data["b64"]}" style="width:100%;border-radius:12px;"></div>'
                break
            # Also check by filename match in slot
            if fn in slot_map:
                s = slot_map[fn]
                if str(s.get("id")) == str(i+1):
                    img_html = f'<div class="hf-animate-2" style="position:absolute;top:60px;right:60px;width:280px"><img src="data:{img_data["mime"]};base64,{img_data["b64"]}" style="width:100%;border-radius:12px;"></div>'
                    break

        # Build page content
        badge = ""
        emoji = ""
        h2_text = title
        lines = narration.split("\\n") if narration else []
        body_lines = "".join(f'<p class="hf-animate-{min(3+j,9)}" style="font-size:20px;color:#555;line-height:1.6;margin-bottom:8px">{l}</p>' for j, l in enumerate(lines[:5]) if l.strip())

        inner = f'''
  <div class="hf-animate-1" style="position:absolute;top:30px;left:80px;background:var(--md-brand,#00d4a4);color:white;border-radius:20px;padding:6px 18px;font-size:17px">{badge or sid}</div>
  <h1 class="hf-animate-2" style="font-size:48px;font-weight:700;color:var(--md-ink,#0a0a0a);margin:80px 80px 20px;line-height:1.2">{emoji} {h2_text}</h1>
  <div style="padding:0 80px">{body_lines}</div>
  {img_html}
  <div class="hf-animate-9" style="position:absolute;bottom:30px;right:40px;font-size:16px;color:#888">{i+1}/{len(pages)}</div>
'''

        html = ch.scene_wrapper(sid, layout, inner, dur)

        if dry_run:
            print(f"  [{layout:12s}] {sid}: {title[:40]} ({dur:.1f}s)")
        else:
            fname = f"scene_{sid}.html" if sid.startswith('s') else f"scene_{i+1}.html"
            with open(os.path.join(comp_dir, fname), "w", encoding="utf-8") as f:
                f.write(html)

        index_pages.append((sid, f"compositions/{fname}", start, dur))

    # 4. Generate index.html
    total_dur = pages[-1].get("end", sum(p.get("duration", 0) for p in pages)) if pages else 0
    idx_html = ch.index_html(index_pages, total_dur)

    if not dry_run:
        idx_path = os.path.join(project, "index.html")
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(idx_html)

    # 5. Verify
    if not dry_run:
        print(f"\nVerifying...")
        ok, total = ch.verify_brand_color(project)
        print(f"  Brand color: {ok}/{total} pages use #00d4a4")
        standalone_ok = 0
        for fname in os.listdir(comp_dir):
            if not fname.endswith(".html"):
                continue
            fp = os.path.join(comp_dir, fname)
            with open(fp) as f:
                c = f.read()
            if "if(top===self)" in c and "tl.progress" in c:
                standalone_ok += 1
        print(f"  Standalone: {standalone_ok}/{len(os.listdir(comp_dir))} pages")

    print(f"\n{'='*60}")
    print(f"Done. {len(pages)} pages → {comp_dir}")
    print(f"{'='*60}")
    return True


if __name__ == "__main__":
    import importlib.util

    dry_run = "--dry-run" in sys.argv
    name = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--dry-run" else \
           (sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--dry-run" else None)

    if not name:
        print("Usage: python3 scripts/render_compositions.py <project> [--dry-run]")
        sys.exit(1)

    project = find_project(name)
    if not project:
        print(f"❌ Project not found: {name}")
        sys.exit(1)

    ok = build_compositions(project, dry_run)
    sys.exit(0 if ok else 1)
