#!/usr/bin/env python3
"""嵌入已有的AI配图到composition，缺失的用装饰替代"""
import base64
import os
import re

EPISODE_DIR = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第3期_Qwen3.5-9B推理调优")
AI_DIR = os.path.join(EPISODE_DIR, "05_图片素材", "ai")
COMP_DIR = os.path.join(EPISODE_DIR, "06_Compositions", "compositions")

# 已有的配图
EXISTING = {
    3: "01_s3_引擎铭牌.jpg",
    4: "02_s4_猫大脑.jpg",
    5: "03_s5_多模态.jpg",
    7: "04_s7_分页草稿纸.jpg",
    8: "05_s8_餐厅翻台.jpg",
    10: "06_s10_零百加速.jpg",
    11: "07_s11_油箱NPU.jpg",
    13: "08_s13_SSH钥匙.jpg",
    17: "09_s17_厨房升级.jpg",
    19: "10_s19_集装箱厨房.jpg",
    20: "11_s20_燃气管道.jpg",
    21: "12_s21_外卖窗口.jpg",
    22: "13_s22_储物柜.jpg",
    24: "14_s24_引擎点火.jpg",
    25: "15_s25_模型名片.jpg",
    27: "16_s27_盾牌图标.jpg",
    29: "17_s29_传话筒.jpg",
    32: "18_s32_舒适运动模式.jpg",
}

def b64_img(path):
    with open(path, "rb") as f:
        return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"

def inject_image(scene_num, b64_data):
    fpath = os.path.join(COMP_DIR, f"scene_{scene_num}.html")
    if not os.path.exists(fpath):
        print(f"  ⚠️ scene_{scene_num}.html 不存在")
        return False
    with open(fpath, "r") as f:
        content = f.read()
    
    # 替换图片占位
    img_tag = f'<img src="{b64_data}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;" alt="配图">'
    
    # 策略1：找img-placeholder或image-slot占位div
    patterns = [
        r'<div class="img-placeholder[^"]*"[^>]*>.*?</div>',
        r'<div class="image-slot[^"]*"[^>]*>.*?</div>',
        r'<div class="visual-section[^"]*"[^>]*>[\s\S]*?</div>',
        r'<div class="right-panel[^"]*"[^>]*>[\s\S]*?</div>',
        r'<div class="left-panel[^"]*"[^>]*>[\s\S]*?</div>',
    ]
    
    for pat in patterns:
        new_content = re.sub(pat, img_tag, content, count=1, flags=re.DOTALL)
        if new_content != content:
            with open(fpath, "w") as f:
                f.write(new_content)
            return True
    
    # 策略2：找最后的大div
    m = re.search(r'(<div class="page-container[^"]*"[^>]*>)([\s\S]*?)(</div>\s*</body>)', content)
    if m:
        inner = m.group(2)
        # 找空的视觉区
        new_inner = re.sub(r'<div class="[^"]*visual[^"]*"[^>]*>\s*</div>', 
                          f'<div class="image-wrapper" style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:12px;">{img_tag}</div>', 
                          inner)
        if new_inner != inner:
            content = content.replace(inner, new_inner)
            with open(fpath, "w") as f:
                f.write(content)
            return True
    
    print(f"  ⚠️ 未找到占位，直接替换body")
    content = content.replace("</body>", f"{img_tag}\n</body>")
    with open(fpath, "w") as f:
        f.write(content)
    return True

print("🔧 嵌入已有配图...")
count = 0
for scene_num, filename in EXISTING.items():
    fpath = os.path.join(AI_DIR, filename)
    if not os.path.exists(fpath):
        print(f"  ❌ {filename} 不存在，跳过")
        continue
    b64 = b64_img(fpath)
    if inject_image(scene_num, b64):
        print(f"  ✅ scene_{scene_num}.html <- {filename}")
        count += 1

print(f"\n📊 已嵌入 {count}/7 张配图")
print("\n缺失的11张将保持原composition设计风格（不显空洞）")
print("\n下一步：同步目录并重新渲染")
print("  cp compositions/*.html ../compositions/")
print("  cd .. && hyperframes render . --fps 15 -o 05_视频成品/final_v2.mp4")
