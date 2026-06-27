"""
v3/config.py — API keys + environment configuration

All API keys are read from environment variables.
Copy .env.example to .env and fill in your keys.
"""
import os
import re
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


# ══════════════════════════════════════════════════════════════
# Naming Convention Constants (v2 规范)
# ══════════════════════════════════════════════════════════════

# Episode directory naming: YYYY-MM-DD_主题_-Agent
EPISODE_NAME_PATTERN = re.compile(
    r'^(\d{4})-(\d{2})-(\d{2})_(.+?)_-(\w+(?:-\w+)*)$'
)
AGENT_NAMES = ["Claude-Code", "Codex", "Hermes"]

# Standardized internal filenames (new pipeline)
# Each step's output files are defined here, so all code references the same name.
# NOTE: compositions/ directory and renders/ are NOT in this list — they are
# managed by HyperFrames engine (external dependency).
FILE_NAMES = {
    # T0
    "topic_report": "00-topic.md",
    # T1
    "outline": "01-outline.md",
    # T2
    "script": "02-script.txt",
    "script_raw": "02-script-raw.txt",
    # T3
    "audio_narration": "03-audio/narration.mp3",
    "audio_srt": "03-audio/narration.srt",
    "audio_ass": "03-audio/narration.ass",
    "timeline": "03-timeline.json",
    # T4
    "storyboard": "04-storyboard.md",
    "image_slots": "04-image-slots.json",
    # T5
    "images_dir": "05-images",
    "image_cache": "05-image-cache.json",
    # Sprites (progress bar runner)
    "sprites_dir": "sprites",
    "sprite_runner": "sprites/runner.png",
    # T6
    "composition": "06-composition.html",
    # T7
    "final_dir": "07-final",
    "final_video": "07-final/final.mp4",
    "raw_video": "07-final/raw.mp4",
    "video_with_audio": "07-final/with-audio.mp4",
    # Pipeline state
    "pipeline_state": "pipeline-state.json",
    # Agent metadata
    "agent_info": ".agent.json",
}

def resolve_episode_path(episode_dir: str, file_key: str) -> str:
    """Resolve a FILE_NAMES key to absolute path.

    Returns the absolute path for a file_key. Only one naming convention
    is used — the values defined in FILE_NAMES above.
    Old-format episodes must be migrated with migrate_episode().
    """
    new_name = FILE_NAMES.get(file_key, file_key)
    return os.path.join(episode_dir, new_name)


def migrate_episode_to_new_naming(episode_dir: str) -> list[str]:
    """Rename old-format files to new-format names in an episode directory.
    Returns list of (old -> new) rename operations performed.
    Useful for one-time migration of legacy episodes.
    """
    import shutil
    ops = []
    old_to_new = {
        "选题研究报告.md": "00-topic.md",
        "知识点大纲.md": "01-outline.md",
        "配音稿_分段.txt": "02-script.txt",
        "配音稿_纯文字.txt": "02-script-raw.txt",
        "PPT大纲.md": "04-storyboard.md",
        "image_slots.json": "04-image-slots.json",
        "index.html": "06-composition.html",
        "pipeline_state.json": "pipeline-state.json",
    }
    for old_name, new_name in old_to_new.items():
        old_path = os.path.join(episode_dir, old_name)
        new_path = os.path.join(episode_dir, new_name)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            ops.append(f"{old_name} -> {new_name}")

    # Migrate subdirectories
    audio_old = os.path.join(episode_dir, "audio")
    audio_new = os.path.join(episode_dir, "03-audio")
    if os.path.isdir(audio_old) and not os.path.isdir(audio_new):
        os.rename(audio_old, audio_new)
        ops.append("audio/ -> 03-audio/")

    images_old = os.path.join(episode_dir, "images")
    images_new = os.path.join(episode_dir, "05-images")
    if os.path.isdir(images_old) and not os.path.isdir(images_new):
        os.rename(images_old, images_new)
        ops.append("images/ -> 05-images/")

    final_old = os.path.join(episode_dir, "成品")
    final_new = os.path.join(episode_dir, "07-final")
    if os.path.isdir(final_old) and not os.path.isdir(final_new):
        os.rename(final_old, final_new)
        ops.append("成品/ -> 07-final/")

    return ops


def validate_episode_name(name: str) -> tuple[bool, str]:
    """Validate new-style episode name: YYYY-MM-DD_主题_-Agent.
    Returns (is_valid, error_message).
    """
    if EPISODE_NAME_PATTERN.match(name):
        return True, ""
    # Also allow legacy "第N期_主题" format
    if re.match(r'^第\d+期_', name):
        return True, ""
    return False, (
        f"Episode name must match 'YYYY-MM-DD_主题_-Agent'\n"
        f"  Example: 2026-06-26_云服务的前世今生_-Claude-Code\n"
        f"  Agent: {', '.join(AGENT_NAMES)}\n"
        f"  Or legacy format: 第N期_主题"
    )


def parse_episode_name(name: str) -> dict:
    """Parse episode name into components.
    Returns dict with keys: date, topic, agent, legacy.
    """
    m = EPISODE_NAME_PATTERN.match(name)
    if m:
        return {
            "date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
            "topic": m.group(4),
            "agent": m.group(5),
            "legacy": False,
        }
    legacy_m = re.match(r'^第\d+期_(.+)', name)
    if legacy_m:
        return {"topic": legacy_m.group(1), "agent": None, "date": None, "legacy": True}
    return {"topic": name, "agent": None, "date": None, "legacy": True}


def get_agent_default() -> str:
    """Detect which agent is calling. Defaults to 'Claude-Code'."""
    return os.environ.get("CODEX_AGENT", "Claude-Code")
