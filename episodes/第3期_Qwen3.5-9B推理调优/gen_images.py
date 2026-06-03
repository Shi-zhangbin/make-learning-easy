#!/usr/bin/env python3
"""批量生成第3期AI配图 - 使用wuyinkeji API"""
import requests
import json
import time
import os
import sys
from PIL import Image
from io import BytesIO

API_KEY = "0BgUoOwfbQSLjWARMMx1APtbKu"
OUTPUT_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第3期_Qwen3.5-9B推理调优/05_图片素材/ai")
os.makedirs(OUTPUT_DIR, exist_ok=True)

IMAGES = [
    # (序号, 文件名, prompt, 目标尺寸)
    ("01", "s3_引擎铭牌", "A close-up of a polished car engine nameplate with engraved text Qwen3.5-9B and 9 Billion Parameters. Dark metallic background with subtle blue glow, film noir style, cinematic lighting, shallow depth of field.", "1280x720"),
    ("02", "s4_猫大脑", "A stylized glowing silhouette of a cat head with a luminous neural network inside the brain area, blue and purple synapses firing, dark background, cinematic volumetric lighting, sci-fi documentary style.", "1280x720"),
    ("03", "s5_多模态", "Split composition showing three input streams converging into one AI model: a photo of a mountain landscape on the left, a data table in the middle, and text paragraphs on the right, all flowing into a glowing central processor. Clean minimal style, flat design.", "1280x720"),
    ("04", "s7_分页草稿纸", "A desk covered with scattered paper sheets transitioning into organized paginated stacks with arrows showing pages moving between a drawer and the desk surface. Minimalist isometric illustration style, clean white and cool blue, like an OS memory management visualization.", "1280x720"),
    ("05", "s8_餐厅翻台", "A busy restaurant interior showing multiple tables at different dining stages: one table being seated, one table eating, one table paying. A waiter carrying multiple dishes between tables. Warm cozy atmosphere, flat vector illustration style.", "1280x720"),
    ("06", "s10_零百加速", "Split comparison: left side shows a sports car speedometer at 0-100 km/h with a stopwatch icon, right side shows a speedometer at max speed with a flame icon. Clean infographic style, dark background with green and blue accent colors, flat design.", "1280x720"),
    ("07", "s11_油箱NPU", "A transparent fuel tank with a gauge showing 4 chambers labeled NPU-0 to NPU-3, each with 24-32GB capacity markings. Fuel level visualization in green gradient. Minimalist tech-infographic style, dark background, cool blue lighting.", "1280x720"),
    ("08", "s13_SSH钥匙", "A glowing golden key unlocking a door that connects a laptop on the left to a distant server room on the right through a network tunnel. The server room visible through the open door shows rows of server racks. Isometric clean tech illustration.", "1280x720"),
    ("09", "s17_厨房升级", "Split comparison of two kitchens: left side a simple home kitchen with just a microwave, right side a professional restaurant kitchen with multiple stoves labeled NPU, Python, PyTorch, vLLM. Clean flat vector illustration, warm lighting.", "1280x720"),
    ("10", "s19_集装箱厨房", "A shipping container transformed into a modular kitchen seen from an isometric angle. Three highlighted areas labeled: --device gas pipe connection, -p takeout window, -v storage cabinet. Clean minimalist flat design, green accent color.", "1280x720"),
    ("11", "s20_燃气管道", "Isometric cutaway view showing 4 gas pipes labeled davinci0-3 connecting from the outside wall into a kitchen interior where a stove burner is lit. Industrial pipes in metallic gray, kitchen in warm orange-tone, clear technical illustration style.", "1280x720"),
    ("12", "s21_外卖窗口", "A kitchen wall with a small takeout window labeled 8010. Through the window you can see someone inside the kitchen cooking. Outside the window a customer is reaching in to pick up an order. Cozy warm illustration style, flat vector art.", "1280x720"),
    ("13", "s22_储物柜", "Split illustration showing two scenarios: left side a person repeatedly downloading from a cloud to an empty locker red X mark, right side a person directly taking a pre-stored model file from a shared locker connected between host and container green checkmark. Clean iconographic style.", "1280x720"),
    ("14", "s24_引擎点火", "A car engine starting with blue electrical sparks jumping between the ECU unit and the engine block. The engine is labeled vLLM and the ECU is labeled Serve Framework. Dramatic cinematic lighting, dark background with electric blue glow.", "1280x720"),
    ("15", "s25_模型名片", "A sleek name card floating in space labeled qwen3.5 with Wi-Fi signal waves radiating outward, connecting to multiple globe icons. Clean minimalist tech illustration, dark background with neon green accents, modern UI concept art style.", "1280x720"),
    ("16", "s27_盾牌图标", "Two icons side by side on a dark background: left a digital shield with a checkmark labeled trust-remote-code, right a gear/shield hybrid labeled enforce-eager. Floating particles connecting them. Clean modern tech-UI style, green and blue neon accents.", "1280x720"),
    ("17", "s29_传话筒", "A communication flow diagram showing a person speaking into a terminal window, data packets traveling through a network pipe to an AI model icon, and response packets traveling back as text output. Clean flat vector illustration with flowing data streams.", "1280x720"),
    ("18", "s32_舒适运动模式", "Split car dashboard view: left side shows a luxury comfort mode with soft blue backlight and smooth indicators, right side shows sport mode with red backlight, aggressive tachometer, and performance gauges. Middle shows a toggle switch. Clean realistic car interior style.", "1280x720"),
]

def submit_image(prompt, size="1280x720"):
    """提交图片生成任务"""
    data = {"key": API_KEY, "prompt": prompt, "size": "16:9"}
    # 用API支持的比例
    resp = requests.post("https://api.wuyinkeji.com/api/async/image_gpt", json=data, timeout=30)
    result = resp.json()
    if result.get("code") == 200:
        return result["data"]["id"]
    else:
        print(f"  提交失败: {result}")
        return None

def poll_result(task_id, max_wait=180):
    """轮询获取结果"""
    start = time.time()
    while time.time() - start < max_wait:
        resp = requests.get(f"https://api.wuyinkeji.com/api/async/detail?key={API_KEY}&id={task_id}", timeout=30)
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
                print(f"  审核失败")
                return None
        time.sleep(3)
    return None

def download_and_save(url, output_path, target_size):
    """下载图片并缩放到目标尺寸"""
    resp = requests.get(url, timeout=60)
    img = Image.open(BytesIO(resp.content))
    # 缩放到目标尺寸
    if target_size:
        w, h = map(int, target_size.split("x"))
        img = img.resize((w, h), Image.LANCZOS)
    img.save(output_path, "JPEG", quality=85)
    return os.path.getsize(output_path)

total = len(IMAGES)
success = 0
failed = []

print(f"🚀 开始生成 {total} 张配图...")
print(f"   输出目录: {OUTPUT_DIR}")
print()

for i, (seq, name, prompt, target_size) in enumerate(IMAGES, 1):
    filename = f"{seq}_{name}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 50000:
        print(f"[{i}/{total}] ⏭️ {filename} 已存在 ({os.path.getsize(filepath)} bytes)")
        success += 1
        continue
    
    print(f"[{i}/{total}] 🎨 生成 {filename}...")
    
    # 提交
    task_id = submit_image(prompt)
    if not task_id:
        print(f"  ❌ 提交失败")
        failed.append(filename)
        continue
    
    # 轮询
    img_url = poll_result(task_id)
    if not img_url:
        print(f"  ❌ 获取结果失败")
        failed.append(filename)
        continue
    
    # 下载
    file_size = download_and_save(img_url, filepath, target_size)
    print(f"  ✅ {filename} ({file_size} bytes)")
    success += 1
    
    # TPM控制
    if i % 3 == 0 and i < total:
        print(f"  ⏳ 批次延迟 10秒...")
        time.sleep(10)
    else:
        time.sleep(3)

print()
print(f"📊 完成: ✅ {success}/{total}")
if failed:
    print(f"❌ 失败: {failed}")
    sys.exit(1)
else:
    print("🎉 全部成功！")
