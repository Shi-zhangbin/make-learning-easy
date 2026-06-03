#!/usr/bin/env python3
"""稳健版：逐张生成配图，每张独立超时"""
import requests
import time
import os
import sys
from PIL import Image
from io import BytesIO

API_KEY = "0BgUoOwfbQSLjWARMMx1APtbKu"
OUTPUT_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第3期_Qwen3.5-9B推理调优/05_图片素材/ai")
os.makedirs(OUTPUT_DIR, exist_ok=True)

IMAGES = [
    ("01", "s3_引擎铭牌", "A close-up of a polished car engine nameplate with engraved text Qwen3.5-9B and 9 Billion Parameters. Dark metallic background with subtle blue glow, film noir style"),
    ("02", "s4_猫大脑", "A stylized glowing silhouette of a cat head with luminous neural network inside the brain area, blue and purple synapses firing, dark background, sci-fi documentary style"),
    ("03", "s5_多模态", "Split composition showing three input streams converging into one AI model: a photo of a mountain landscape, a data table, and text paragraphs, all flowing into a glowing central processor. Flat design"),
    ("04", "s7_分页草稿纸", "A desk covered with scattered paper sheets transitioning into organized paginated stacks with arrows showing pages moving between drawer and desk surface. Minimalist isometric style"),
    ("05", "s8_餐厅翻台", "A busy restaurant interior showing multiple tables at different dining stages: one being seated, one eating, one paying. A waiter carrying multiple dishes. Flat vector illustration"),
    ("06", "s10_零百加速", "Split comparison: left shows sports car speedometer at 0-100 km/h with stopwatch, right shows speedometer at max speed with flame icon. Clean infographic style, dark background"),
    ("07", "s11_油箱NPU", "A transparent fuel tank with gauge showing 4 chambers labeled NPU-0 to NPU-3, each with capacity markings. Fuel level in green gradient. Tech-infographic style, dark background"),
    ("08", "s13_SSH钥匙", "A glowing golden key unlocking a door connecting a laptop to a distant server room through a network tunnel. Isometric clean tech illustration, dark background with blue lighting"),
    ("09", "s17_厨房升级", "Split comparison of two kitchens: left simple home kitchen with microwave, right professional restaurant kitchen with stoves labeled NPU, Python, PyTorch, vLLM. Flat vector art"),
    ("10", "s19_集装箱厨房", "A shipping container transformed into modular kitchen, isometric angle. Three areas labeled: --device gas pipe, -p takeout window, -v storage cabinet. Clean minimalist flat design"),
    ("11", "s20_燃气管道", "Isometric cutaway view showing 4 gas pipes labeled davinci0-3 connecting from outside wall into kitchen interior. Industrial pipes in gray, kitchen in warm orange-tone"),
    ("12", "s21_外卖窗口", "A kitchen wall with small takeout window labeled 8010. Through the window someone inside is cooking, outside a customer reaches in to pick up order. Flat vector art, cozy style"),
    ("13", "s22_储物柜", "Split: left side a person repeatedly downloading from cloud to empty locker (red X), right side a person taking pre-stored model from shared locker (green checkmark). Clean style"),
    ("14", "s24_引擎点火", "A car engine starting with blue electrical sparks between ECU unit and engine block. Engine labeled vLLM, ECU labeled Serve Framework. Dramatic lighting, dark background"),
    ("15", "s25_模型名片", "A sleek name card floating in space labeled qwen3.5 with Wi-Fi signal waves radiating outward to globe icons. Minimalist tech illustration, dark background, neon green accents"),
    ("16", "s27_盾牌图标", "Two icons side by side: left digital shield with checkmark labeled trust-remote-code, right gear/shield hybrid labeled enforce-eager. Tech-UI style, green and blue neon accents"),
    ("17", "s29_传话筒", "Communication flow diagram: person speaking into terminal, data packets through network pipe to AI model icon, response packets back as text. Flat vector with flowing data streams"),
    ("18", "s32_舒适运动模式", "Split car dashboard: left luxury comfort mode with soft blue backlight, right sport mode with red backlight and performance gauges. Middle shows toggle switch. Realistic car interior"),
]

def generate_one(prompt, output_path, max_wait=180):
    """提交+轮询+下载一张图"""
    try:
        resp = requests.post(
            "https://api.wuyinkeji.com/api/async/image_gpt",
            json={"key": API_KEY, "prompt": prompt, "size": "16:9"},
            timeout=30
        )
        result = resp.json()
        if result.get("code") != 200:
            return False, f"提交失败: {result}"
        task_id = result.get("data", {}).get("id")
        if not task_id:
            return False, "无task_id"
        
        # 轮询
        start = time.time()
        while time.time() - start < max_wait:
            time.sleep(3)
            poll_resp = requests.get(
                f"https://api.wuyinkeji.com/api/async/detail?key={API_KEY}&id={task_id}",
                timeout=30
            )
            poll_result = poll_resp.json()
            if poll_result.get("code") != 200:
                continue
            data = poll_result.get("data")
            if data is None:
                continue
            status = data.get("status")
            if status == 2:
                urls = data.get("result", [])
                if urls and isinstance(urls, list):
                    img_url = urls[0]
                    # 下载
                    img_resp = requests.get(img_url, timeout=60)
                    img = Image.open(BytesIO(img_resp.content))
                    img = img.resize((1280, 720), Image.LANCZOS)
                    img.save(output_path, "JPEG", quality=85)
                    size = os.path.getsize(output_path)
                    return True, f"{size} bytes"
            elif status == 3:
                return False, "审核失败"
        return False, "超时"
    except Exception as e:
        return False, str(e)

total = len(IMAGES)
success = 0
failed = []
print(f"🚀 开始逐张生成 {total} 张配图...")
print()

for i, (seq, name, prompt) in enumerate(IMAGES, 1):
    filename = f"{seq}_{name}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 50000:
        print(f"[{i}/{total}] ⏭️ {filename} 已存在")
        success += 1
        continue
    
    print(f"[{i}/{total}] 🎨 生成 {filename}... ", end="", flush=True)
    ok, msg = generate_one(prompt, filepath)
    if ok:
        print(f"✅ {msg}")
        success += 1
    else:
        print(f"❌ {msg}")
        failed.append(filename)
    
    # 温和节流
    time.sleep(2)

print(f"\n📊 结果: ✅ {success}/{total}")
if failed:
    print(f"❌ 失败: {failed}")
else:
    print("🎉 全部成功！")
