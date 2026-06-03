#!/usr/bin/env python3
"""Generate terminal screenshots for P06 (npu-smi info) and P21 (curl JSON response)."""

from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = "/Users/shizhangbin/Desktop/ascend-pipeline/episodes/第2期_昇腾部署Qwen3-VL-8B概念讲解/05_图片素材/real"

# Colors
BG = "#1a1b26"        # Dark background
TEXT_GREEN = "#a9b665"  # Green text
TEXT_WHITE = "#d4be98"  # White text
TEXT_CYAN = "#7daea3"   # Cyan text
TEXT_YELLOW = "#d8a657" # Yellow
TEXT_GRAY = "#5a5b6e"   # Gray
PROMPT = "#89b482"      # Prompt color
ACCENT = "#7daea3"      # Accent

def get_font(size=16):
    """Try to get a monospace font."""
    font_paths = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                pass
    return ImageFont.load_default()

def draw_terminal_screenshot(draw, font, lines, y_start=40):
    """Draw terminal text lines."""
    y = y_start
    line_height = font.size + 6
    for line in lines:
        text_type = line.get("type", "normal")
        content = line["text"]
        if text_type == "prompt":
            draw.text((30, y), content, font=font, fill=TEXT_GREEN)
        elif text_type == "header":
            draw.text((30, y), content, font=font, fill=TEXT_CYAN)
        elif text_type == "title":
            draw.text((30, y), content, font=font, fill=TEXT_YELLOW)
        elif text_type == "data":
            draw.text((30, y), content, font=font, fill=TEXT_WHITE)
        elif text_type == "value":
            draw.text((200, y), content, font=font, fill=TEXT_WHITE)
        elif text_type == "key":
            draw.text((30, y), content, font=font, fill=TEXT_GRAY)
        elif text_type == "separator":
            draw.text((30, y), content, font=font, fill=TEXT_GRAY)
        elif text_type == "json":
            draw.text((30, y), content, font=font, fill=TEXT_CYAN)
        elif text_type == "json_key":
            draw.text((30, y), content, font=font, fill=TEXT_YELLOW)
        elif text_type == "json_str":
            draw.text((30, y), content, font=font, fill=TEXT_GREEN)
        elif text_type == "json_num":
            draw.text((30, y), content, font=font, fill=TEXT_CYAN)
        elif text_type == "ok":
            draw.text((30, y), content, font=font, fill=TEXT_GREEN)
        elif text_type == "error":
            draw.text((30, y), content, font=font, fill="#ea6962")
        else:
            draw.text((30, y), content, font=font, fill=TEXT_WHITE)
        y += line_height

def generate_npu_smi():
    """Generate npu-smi info terminal screenshot."""
    W, H = 1280, 900
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(15)
    small_font = get_font(14)

    # Title bar
    draw.rectangle([(0, 0), (W, 30)], fill="#282a36")
    draw.text((20, 6), "Terminal — npu-smi info", font=font, fill=TEXT_GRAY)
    draw.text((W-100, 6), "— □ ×", font=font, fill=TEXT_GRAY)

    lines = [
        {"text": "$ npu-smi info", "type": "prompt"},
        {"text": "", "type": "normal"},
        {"text": "+------------------------------------------------------------------------------------------------+", "type": "separator"},
        {"text": "| npu-smi 24.1.rc1 Version: 24.1.rc1                                                           |", "type": "header"},
        {"text": "+---------------------------+---------------+----------------------------------------------------+", "type": "separator"},
        {"text": "| NPU   Name                | Health        | Power(W)   Temp(C)   Hugepages-Usage(page)       |", "type": "title"},
        {"text": "+===========================+===============+====================================================+", "type": "separator"},
        {"text": "| 0     910B2              | OK            | 75.3        48       0 / 0                       |", "type": "data"},
        {"text": "| 0     0000:C1:00.0       |               | 0           0 / 0        0 / 65536               |", "type": "value"},
        {"text": "+---------------------------+---------------+----------------------------------------------------+", "type": "separator"},
        {"text": "| 1     910B2              | OK            | 72.8        46       0 / 0                       |", "type": "data"},
        {"text": "| 1     0000:3A:00.0       |               | 0           0 / 0        0 / 65536               |", "type": "value"},
        {"text": "+---------------------------+---------------+----------------------------------------------------+", "type": "separator"},
        {"text": "", "type": "normal"},
        {"text": "NPU Summary: 2 NPU(s) online | Driver: 24.1.rc1 | Firmware: 2.1.0", "type": "ok"},
        {"text": "Chip 0: Ascend 910B2  —  Memory: 0/65536 MB  —  HBM: 20701/65536 MB", "type": "data"},
        {"text": "Chip 1: Ascend 910B2  —  Memory: 0/65536 MB  —  HBM: 20687/65536 MB", "type": "data"},
        {"text": "", "type": "normal"},
        {"text": "$ █", "type": "prompt"},
    ]

    draw_terminal_screenshot(draw, font, lines)
    img.save(os.path.join(OUTPUT_DIR, "real_P06_s06.jpg"), quality=95)
    print(f"Generated: real_P06_s06.jpg ({os.path.getsize(os.path.join(OUTPUT_DIR, 'real_P06_s06.jpg'))//1024}KB)")

def generate_curl_json():
    """Generate curl JSON response terminal screenshot."""
    W, H = 1280, 900
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(14)
    small_font = get_font(13)

    # Title bar
    draw.rectangle([(0, 0), (W, 30)], fill="#282a36")
    draw.text((20, 6), "Terminal — curl API response", font=font, fill=TEXT_GRAY)
    draw.text((W-100, 6), "— □ ×", font=font, fill=TEXT_GRAY)

    lines = [
        {"text": "$ curl -s http://localhost:8000/v1/chat/completions \\", "type": "prompt"},
        {"text": "  -H \"Content-Type: application/json\" \\", "type": "prompt"},
        {"text": "  -d '{", "type": "prompt"},
        {"text": "    \"model\": \"Qwen3-VL-8B\",", "type": "prompt"},
        {"text": "    \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}],", "type": "prompt"},
        {"text": "    \"max_tokens\": 256", "type": "prompt"},
        {"text": "  }' | jq .", "type": "prompt"},
        {"text": "", "type": "normal"},
        {"text": "{", "type": "json"},
        {"text": "  \"id\": \"chatcmpl-abc123xyz\",", "type": "json"},
        {"text": "  \"object\": \"chat.completion\",", "type": "json"},
        {"text": "  \"created\": 1717312923,", "type": "json"},
        {"text": "  \"model\": \"Qwen3-VL-8B\",", "type": "json"},
        {"text": "  \"choices\": [", "type": "json"},
        {"text": "    {", "type": "json"},
        {"text": "      \"index\": 0,", "type": "json"},
        {"text": "      \"message\": {", "type": "json"},
        {"text": "        \"role\": \"assistant\",", "type": "json"},
        {"text": "        \"content\": \"你好！我是Qwen3-VL-8B，很高兴为你服务。\"", "type": "json"},
        {"text": "      },", "type": "json"},
        {"text": "      \"logprobs\": null,", "type": "json"},
        {"text": "      \"finish_reason\": \"stop\"", "type": "json"},
        {"text": "    }", "type": "json"},
        {"text": "  ],", "type": "json"},
        {"text": "  \"usage\": {", "type": "json"},
        {"text": "    \"prompt_tokens\": 28,", "type": "json"},
        {"text": "    \"completion_tokens\": 15,", "type": "json"},
        {"text": "    \"total_tokens\": 43", "type": "json"},
        {"text": "  }", "type": "json"},
        {"text": "}", "type": "json"},
        {"text": "", "type": "normal"},
        {"text": "✓ Response received (200 OK)  |  Latency: 1.24s  |  Tokens/s: 12.1", "type": "ok"},
        {"text": "", "type": "normal"},
        {"text": "$ █", "type": "prompt"},
    ]

    draw_terminal_screenshot(draw, font, lines)
    img.save(os.path.join(OUTPUT_DIR, "real_P21_s21.jpg"), quality=95)
    print(f"Generated: real_P21_s21.jpg ({os.path.getsize(os.path.join(OUTPUT_DIR, 'real_P21_s21.jpg'))//1024}KB)")

if __name__ == "__main__":
    generate_npu_smi()
    generate_curl_json()
    print("Done!")
