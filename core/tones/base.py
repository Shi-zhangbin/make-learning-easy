"""
core/tones/base.py — Tone preset loader

Loads a tone YAML definition, provides the script_style_guide,
tone_style, and validation_rules for a given narration voice.
"""
import yaml
from pathlib import Path

TONES_DIR = Path(__file__).resolve().parent


def load_tone(name: str) -> dict:
    """Load a tone preset by name (e.g. 'bilibili-upzhu', 'talk-show')."""
    path = TONES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Tone preset not found: {name} (tried {path})")
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw or {}


def list_tones() -> list[dict]:
    """List all available tone presets."""
    results = []
    for f in sorted(TONES_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if raw and "name" in raw:
            results.append({
                "name": raw["name"],
                "display_name": raw.get("display_name", f.stem),
                "description": raw.get("description", ""),
            })
    return results
