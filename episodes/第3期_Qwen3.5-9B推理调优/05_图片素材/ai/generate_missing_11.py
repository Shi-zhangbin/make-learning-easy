#!/usr/bin/env python3
"""
生成第3期缺失的11张AI配图
策略: 优先wuyinkeji API -> 失败则Unsplash/Pixabay下载替代
"""
import requests
import time
import os
import sys
import json
import urllib.parse
from PIL import Image, Image as PILImage
from io import BytesIO
import random

# Pillow compat - LANCZOS might be deprecated in newer versions
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.LANCZOS

API_KEY = "0BgUoOwfbQSLjWARMMx1APtbKu"
OUTPUT_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第3期_Qwen3.5-9B推理调优/05_图片素材/ai")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 11张缺失配图 - 使用任务指定的精确prompt
IMAGES = [
    {
        "seq": "07",
        "name": "s11_油箱NPU",
        "prompt": "transparent fuel tank with 4 chambers labeled NPU-0 to NPU-3, fuel gauge, tech infographic, clean dark background, 16:9",
        "fallback_query": "transparent fuel tank chambers tech diagram"
    },
    {
        "seq": "09",
        "name": "s17_厨房升级",
        "prompt": "split comparison simple home kitchen vs professional restaurant kitchen with many stoves, flat vector illustration, clean white background",
        "fallback_query": "kitchen comparison simple professional flat vector"
    },
    {
        "seq": "10",
        "name": "s19_集装箱厨房",
        "prompt": "isometric shipping container transformed into modular kitchen, three highlighted sections, minimalist flat design, white background",
        "fallback_query": "isometric shipping container modular kitchen"
    },
    {
        "seq": "11",
        "name": "s20_燃气管道",
        "prompt": "isometric view of gas pipes connecting from outside to kitchen interior, 4 pipes labeled davinci, technical illustration style",
        "fallback_query": "gas pipes connection technical diagram isometric"
    },
    {
        "seq": "12",
        "name": "s21_外卖窗口",
        "prompt": "kitchen wall with small takeout window labeled 8010, someone cooking inside, customer outside, flat vector illustration, warm colors",
        "fallback_query": "takeout window kitchen restaurant illustration"
    },
    {
        "seq": "13",
        "name": "s22_储物柜",
        "prompt": "split comparison of two storage lockers, left with red X downloading from cloud, right with green checkmark taking from shared locker, clean iconographic style",
        "fallback_query": "cloud storage comparison lockers infographic"
    },
    {
        "seq": "14",
        "name": "s24_引擎点火",
        "prompt": "car engine starting with blue electrical sparks, ECU labeled vLLM, engine block, dramatic cinematic lighting, dark background",
        "fallback_query": "car engine starting electrical sparks cinematic"
    },
    {
        "seq": "15",
        "name": "s25_模型名片",
        "prompt": "sleek name card floating in space labeled qwen3.5, Wi-Fi signals radiating, globe icons, minimalist tech illustration, dark background",
        "fallback_query": "floating name card technology digital minimalist"
    },
    {
        "seq": "16",
        "name": "s27_盾牌图标",
        "prompt": "two icons side by side, left digital shield with checkmark labeled trust-remote-code, right gear labeled enforce-eager, tech-UI style",
        "fallback_query": "digital shield gear icons cyber security UI"
    },
    {
        "seq": "17",
        "name": "s29_传话筒",
        "prompt": "communication flow diagram, person speaking into terminal, data packets through network pipe to AI model, response back, clean flat vector",
        "fallback_query": "communication flow diagram data network flat vector"
    },
    {
        "seq": "18",
        "name": "s32_舒适运动模式",
        "prompt": "split car dashboard, left comfort mode with blue backlight, right sport mode with red backlight and performance gauges, realistic style",
        "fallback_query": "car dashboard comfort sport mode dual split"
    },
]

# Unsplash API (free, no key needed for basic search)
UNSPLASH_ACCESS_KEY = None  # Using Pixabay instead which is more reliable without key

def submit_wuyinkeji(prompt):
    """提交wuyinkeji AI绘图任务"""
    try:
        data = {"key": API_KEY, "prompt": prompt, "size": "16:9"}
        resp = requests.post(
            "https://api.wuyinkeji.com/api/async/image_gpt",
            json=data, timeout=30
        )
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data", {}).get("id")
        else:
            print(f"   提交失败: code={result.get('code')}, msg={result.get('msg', '')}")
            return None
    except Exception as e:
        print(f"   提交异常: {e}")
        return None

def poll_wuyinkeji(task_id, max_wait=180):
    """轮询wuyinkeji任务结果"""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            # key放在query参数
            resp = requests.get(
                f"https://api.wuyinkeji.com/api/async/detail?key={API_KEY}&id={task_id}",
                timeout=30
            )
            result = resp.json()
            if result.get("code") == 200:
                data = result.get("data")
                if data is None:
                    time.sleep(3)
                    continue
                status = data.get("status")
                if status == 2:  # 完成
                    urls = data.get("result", [])
                    if urls and isinstance(urls, list):
                        return urls[0]
                elif status == 3:  # 审核失败
                    print(f"   审核不通过(status=3)")
                    return None
                elif status == 4:  # 失败
                    print(f"   生成失败(status=4)")
                    return None
            time.sleep(3)
        except Exception as e:
            print(f"   轮询异常: {e}")
            time.sleep(5)
    return None

def download_image_wuyinkeji(img_url, output_path):
    """从wuyinkeji下载图片并处理"""
    try:
        resp = requests.get(img_url, timeout=60)
        img = Image.open(BytesIO(resp.content))
        img = img.resize((1280, 720), RESAMPLE)
        img.save(output_path, "JPEG", quality=85)
        size = os.path.getsize(output_path)
        return True, size
    except Exception as e:
        return False, str(e)

def try_wuyinkeji(prompt, output_path):
    """尝试wuyinkeji API生成一张图"""
    print(f"   📤 提交wuyinkeji...", end=" ", flush=True)
    task_id = submit_wuyinkeji(prompt)
    if not task_id:
        print("❌ 提交失败")
        return False
    
    print(f"task_id={task_id}, 轮询中...", end=" ", flush=True)
    img_url = poll_wuyinkeji(task_id)
    if not img_url:
        print("❌ 获取结果失败")
        return False
    
    print("下载中...", end=" ", flush=True)
    ok, result = download_image_wuyinkeji(img_url, output_path)
    if ok:
        print(f"✅ {result/1024:.0f}KB")
        return True
    else:
        print(f"❌ {result}")
        return False

# === Pixabay fallback ===
PIXABAY_KEY = "48309800-2ba5114d04f7a09b664169587"  # free API key

def search_pixabay(query, per_page=20):
    """Search Pixabay for free images"""
    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_KEY,
        "q": urllib.parse.quote(query),
        "image_type": "illustration",
        "orientation": "horizontal",
        "per_page": per_page,
        "safesearch": "true",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data.get("totalHits", 0) > 0:
            hits = data.get("hits", [])
            # Try large image first, then medium
            for hit in hits:
                if hit.get("largeImageURL"):
                    return hit["largeImageURL"]
            if hits[0].get("webformatURL"):
                return hits[0]["webformatURL"]
        return None
    except Exception as e:
        print(f"   Pixabay搜索异常: {e}")
        return None

def search_unsplash(query):
    """Search Unsplash for free photos"""
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "orientation": "landscape",
        "per_page": 5,
    }
    headers = {}
    if UNSPLASH_ACCESS_KEY:
        headers["Authorization"] = f"Client-ID {UNSPLASH_ACCESS_KEY}"
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        results = data.get("results", [])
        if results:
            return results[0]["urls"]["regular"]
        return None
    except Exception as e:
        print(f"   Unsplash搜索异常: {e}")
        return None

def download_fallback(img_url, output_path):
    """下载fallback图片并resize到1280x720"""
    try:
        resp = requests.get(img_url, timeout=60)
        img = Image.open(BytesIO(resp.content))
        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img = img.resize((1280, 720), RESAMPLE)
        img.save(output_path, "JPEG", quality=85)
        size = os.path.getsize(output_path)
        return True, size
    except Exception as e:
        return False, str(e)

def try_fallback(query, output_path):
    """Fallback: search and download free image"""
    print(f"   🔍 搜索免费图: '{query}'...", end=" ", flush=True)
    
    # Try Pixabay first
    img_url = search_pixabay(query)
    if not img_url:
        # Try Unsplash
        img_url = search_unsplash(query)
    
    if not img_url:
        print("❌ 未找到免费图")
        return False
    
    print(f"下载中...", end=" ", flush=True)
    ok, result = download_fallback(img_url, output_path)
    if ok:
        print(f"✅ {result/1024:.0f}KB")
        return True
    else:
        print(f"❌ {result}")
        return False

# ===== Main =====
total = len(IMAGES)
success = 0
failed = []

print(f"🚀 第3期 生成缺失 {total} 张配图")
print(f"   输出目录: {OUTPUT_DIR}")
print()

for i, img_info in enumerate(IMAGES, 1):
    seq = img_info["seq"]
    name = img_info["name"]
    prompt = img_info["prompt"]
    fallback_query = img_info["fallback_query"]
    
    filename = f"{seq}_{name}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Skip if already exists
    if os.path.exists(filepath) and os.path.getsize(filepath) > 50000:
        print(f"[{i}/{total}] ⏭️ {filename} 已存在 ({os.path.getsize(filepath)/1024:.0f}KB)")
        success += 1
        continue
    
    print(f"[{i}/{total}] 🎨 {filename}")
    print(f"   Prompt: {prompt[:60]}...")
    
    # Try wuyinkeji API first
    ok = try_wuyinkeji(prompt, filepath)
    
    if not ok:
        print(f"   ⚠️ wuyinkeji失败，尝试免费替代图...")
        ok = try_fallback(fallback_query, filepath)
    
    if ok:
        success += 1
    else:
        print(f"   ❌ 所有方法失败")
        failed.append(filename)
    
    print()  # blank line between images
    
    # Rate limiting
    if i < total:
        time.sleep(2)

print("=" * 50)
print(f"📊 结果: ✅ {success}/{total}")
if failed:
    print(f"❌ 失败: {failed}")
    sys.exit(1)
else:
    print("🎉 全部成功！")
