"""
v3/config.py — API keys + environment configuration

All API keys are read from environment variables.
Copy .env.example to .env and fill in your keys.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Image Generation API Keys ──
WUYINKEJI_KEY = os.environ.get("WUYINKEJI_KEY", "")
WUYINKEJI_BASE = "https://api.wuyinkeji.com/api/async"
WUYINKEJI_SUBMIT_URL = f"{WUYINKEJI_BASE}/image_gpt"
WUYINKEJI_DETAIL_URL = f"{WUYINKEJI_BASE}/detail"

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "")

# ── Image Generation Fallback Chain ──
IMAGE_FALLBACK_CHAIN = ["wuyinkeji", "pexels", "pixabay", "svg"]

# ── TTS ──
EDGE_TTS_VOICE = "zh-CN-XiaoxiaoNeural"
EDGE_TTS_RATE = "+15%"
TTS_EFFECTIVE_CHARS_PER_SEC = 4.2

# ── Image Quality ──
# ffmpeg -q:v scale: 2=best, 7=smallest, 6≈balanced
IMAGE_JPEG_QUALITY = 6
# PIL PNG compress level: 0-9, 6=default
IMAGE_PNG_COMPRESSION = 6


# ── Video ──
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 15

WUYINKEJI_SIZE_MAP = {
    "16:9": "16:9", "1:1": "1:1", "4:3": "4:3",
    "3:2": "3:2", "2:3": "2:3", "9:16": "9:16",
    "21:9": "21:9", "3:4": "3:4", "auto": "auto",
}

# ── Project paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPISODES_DIR = os.path.join(BASE_DIR, "episodes")
V3_DIR = os.path.join(BASE_DIR, "v3")
PRESETS_DIR = os.path.join(V3_DIR, "designs", "presets")
TEMPLATES_DIR = os.path.join(V3_DIR, "templates")
LAYOUTS_DIR = os.path.join(TEMPLATES_DIR, "layouts")
