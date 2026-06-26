#!/usr/bin/env python3
"""
generate_images.py — 从 image_slots.json 生成配图到 images/

用法:
  python3 scripts/generate_images.py <项目目录>
  python3 scripts/generate_images.py <项目目录> --api openai
  python3 scripts/generate_images.py <项目目录> --dry-run   # 只列不生成

流程:
  1. 扫描项目下 image_slots.json
  2. 检查 images/ 目录是否已有 filename
  3. 缺失的图片调用 API 生成（默认 openai）
  4. 完成后调用 images_to_base64.py → images_b64.json
"""

import argparse, json, os, sys, base64, io, glob, subprocess
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def find_slots(project):
    """Find image_slots.json anywhere under project."""
    for root, dirs, files in os.walk(project):
        if "image_slots.json" in files:
            return os.path.join(root, "image_slots.json")
    return None


def load_slots(slots_path):
    with open(slots_path) as f:
        data = json.load(f)
    # Handle multiple formats:
    # 1. Direct list: [...]  
    # 2. Dict with "slots": [...]
    # 3. Dict with "data": [...]
    slot_list = []
    if isinstance(data, dict):
        slot_list = data.get("slots", data.get("data", []))
    elif isinstance(data, list):
        slot_list = data
    if not isinstance(slot_list, list):
        slot_list = []
    # Auto-detect AI slots: any slot with a "prompt" field is AI
    for s in slot_list:
        if isinstance(s, dict):
            if "source" not in s and s.get("prompt"):
                s["source"] = "ai"
    return slot_list


def wuyinkeji_generate(prompt, filename, out_dir):
    """Generate image via wuyinkeji async API (status=2=done, param=id)."""
    api_key = os.environ.get("WUYINKEJI_KEY", "")
    if not api_key:
        print(f"  WUYINKEJI_KEY not set, skip {filename}")
        return False
    if not HAS_REQUESTS:
        print(f"  requests not installed, skip {filename}")
        return False

    import time
    base = "https://api.wuyinkeji.com/api/async"

    # Submit
    try:
        r = requests.post(f"{base}/image_gpt",
            json={"prompt": prompt, "size": "1792x1024", "key": api_key}, timeout=15)
        resp = r.json()
        if resp.get("code") != 200:
            print(f"  X {filename}: submit fail - {resp.get('msg','?')}")
            return False
        img_id = resp["data"]["id"]
    except Exception as e:
        print(f"  X {filename}: submit error - {e}")
        return False

    # Poll (param: id=, status: 2=done, -1=failed)
    for attempt in range(60):
        time.sleep(5)
        try:
            r = requests.get(f"{base}/detail",
                params={"id": img_id, "key": api_key}, timeout=15)
            resp = r.json()
            if resp.get("code") != 200:
                continue
            status = resp.get("data", {}).get("status", 0)
            if status == 2:
                urls = resp.get("data", {}).get("result", [])
                if urls:
                    img_r = requests.get(urls[0], timeout=60)
                    out_path = os.path.join(out_dir, filename)
                    with open(out_path, "wb") as f:
                        f.write(img_r.content)
                    if HAS_PIL:
                        from PIL import Image
                        img = Image.open(out_path)
                        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                        w, h = img.size
                        # Keep resolution for HD video (min 1920 width)
                        if w > 3840:
                            s = 3840 / w
                            img = img.resize((int(w*s), int(h*s)), Image.LANCZOS)
                        img.save(out_path, "JPEG", quality=95, optimize=True)
                    print(f"  OK {filename} ({os.path.getsize(out_path)//1024}KB)")
                    return True
            elif status == -1:
                print(f"  X {filename}: generate failed")
                return False
        except Exception as e:
            if attempt < 3: continue
            print(f"  X {filename}: poll error - {e}")
            return False
    print(f"  - {filename}: timeout")
    return False
# def openai_generate(...) 已移除 — 管线仅使用 wuyinkeji (image2) API
# 如需恢复 OpenAI DALL-E 回退，可参考 git history 恢复此函数


def generate_images(project, api="wuyinkeji", dry_run=False):
    """Main generation logic."""
    slots_path = find_slots(project)
    if not slots_path:
        print("❌ 未找到 image_slots.json")
        return False

    slot_list = load_slots(slots_path)
    ai_slots = [s for s in slot_list if isinstance(s, dict) and s.get("source") == "ai"]
    real_slots = [s for s in slot_list if isinstance(s, dict) and s.get("source") == "real"]

    img_dir = os.path.join(project, "images")
    os.makedirs(img_dir, exist_ok=True)

    print(f"\n📋 image_slots.json: {os.path.relpath(slots_path, os.path.dirname(project))}")
    print(f"   共 {len(slot_list)} 个 slot：{len(ai_slots)} AI + {len(real_slots)} real")
    print(f"   输出: {img_dir}")

    # 检查已有图片
    existing_files = set()
    for f in glob.glob(os.path.join(img_dir, "*.*")):
        existing_files.add(os.path.basename(f))

    pending = []
    for slot in ai_slots:
        fn = slot.get("filename", f"p{slot.get('id',0):02d}_{slot.get('slot','main')}.jpg")
        if fn in existing_files:
            print(f"  ✅ 已有: {fn}  ({os.path.getsize(os.path.join(img_dir, fn))//1024}KB)")
        else:
            pending.append((slot, fn))
            if dry_run:
                print(f"  📝 待生成: {fn}  ← {slot.get('content','')[:50]}")

    if dry_run:
        print(f"\n📊 待生成: {len(pending)}/{len(ai_slots)}")
        if pending:
            print("\n生成命令:")
            print(f"  python3 scripts/generate_images.py \"{project}\"")
        return True

    # 生成缺失图片
    if not pending:
        print(f"\n✅ 所有 {len(ai_slots)} 张 AI 配图已存在")
    else:
        print(f"\n🖼️  生成 {len(pending)} 张缺失配图...")
        success = 0
        for slot, fn in pending:
            prompt = slot.get("prompt") or slot.get("content", "")
            size = slot.get("size", "1024x1024")
            # size 映射
            size_map = {
                "full": "1792x1024",
                "wide": "1792x1024",
                "640x360": "1024x576",
                "320x180": "1024x576",
            }
            api_size = size_map.get(size, "1792x1024")

            # 仅使用 wuyinkeji (image2) API，无需 OPENAI_API_KEY
            ok = wuyinkeji_generate(prompt, fn, img_dir)
            if ok:
                success += 1

        print(f"\n📊 生成结果: {success}/{len(pending)}")

    # 生成 base64 映射
    script_dir = os.path.dirname(os.path.abspath(__file__))
    b64_script = os.path.join(script_dir, "images_to_base64.py")
    if os.path.exists(b64_script):
        out_json = os.path.join(img_dir, "..", "images_b64.json")
        subprocess.run(
            [sys.executable, b64_script, "--dir", img_dir,
             "--out", out_json, "--quality", "85"],
            check=False,
        )
        if os.path.exists(out_json):
            print(f"  ✅ base64 映射: {os.path.relpath(out_json, project)}")

    return True


def main():
    p = argparse.ArgumentParser(description="从 image_slots.json 生成配图")
    p.add_argument("project", help="项目目录路径或名称")
    p.add_argument("--api", default="wuyinkeji", choices=["wuyinkeji"], help="图片生成 API（仅 wuyinkeji）")
    p.add_argument("--dry-run", action="store_true", help="只列出，不生成")

    args = p.parse_args()

    # 解析项目路径
    base = os.path.expanduser("~/Desktop/ascend-pipeline")
    project = args.project
    if not os.path.isabs(project):
        for d in [os.path.join(base, "episodes", project), os.path.join(base, project)]:
            if os.path.isdir(d):
                project = d
                break

    if not os.path.isdir(project):
        print(f"❌ 项目目录不存在: {args.project}")
        sys.exit(1)

    ok = generate_images(project, "wuyinkeji", args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

