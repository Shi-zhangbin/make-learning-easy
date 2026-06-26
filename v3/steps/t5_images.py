"""
v3/steps/t5_images.py — Image generation step

Generates all images from image_slots.json using the three-tier
fallback chain: wuyinkeji → pexels → pixabay → svg
"""
import json, os
from pathlib import Path
from v3.config import FILE_NAMES
from v3.steps.base import StepHandler, StepResult
from v3.imagegen import generate_all_images


class ImageHandler(StepHandler):
    name = "T5"
    description = "Generate all images from image_slots.json"

    def _find_slots(self) -> list[dict]:
        """Find and parse image_slots.json in the episode directory."""
        json_path = None
        # Try new naming first
        new_path = self.episode_dir / FILE_NAMES["image_slots"]
        if new_path.exists():
            json_path = new_path
        else:
            # Legacy fallback
            for f in self.episode_dir.rglob("image_slots.json"):
                json_path = f
                break
        if not json_path:
            raise FileNotFoundError("No image_slots.json found in episode directory")

        with open(json_path) as f:
            data = json.load(f)

        slots = []
        if isinstance(data, dict):
            slots = data.get("slots", data.get("data", []))
        elif isinstance(data, list):
            slots = data
        # Ensure AI slots are tagged
        for s in slots:
            if isinstance(s, dict) and "source" not in s and s.get("prompt"):
                s["source"] = "ai"
        return slots

    def execute(self) -> StepResult:
        slots = self._find_slots()
        ai_slots = [s for s in slots if isinstance(s, dict) and s.get("source") == "ai"]

        if not ai_slots:
            print("  No AI image slots found. Skipping T5.")
            return StepResult(True, {"generated": 0, "images": {}})

        img_dir = str(self.episode_dir / FILE_NAMES["images_dir"])
        print(f"  Generating {len(ai_slots)} images -> {img_dir}")

        images = generate_all_images(ai_slots, img_dir, self.design)

        # Generate base64 cache for T6
        b64_cache = {}
        for fn in images:
            b64_cache[fn] = images[fn]
        cache_path = self.episode_dir / FILE_NAMES["image_cache"]
        with open(cache_path, "w") as f:
            json.dump(b64_cache, f, ensure_ascii=False)

        print(f"  Generated {len(images)} images (+ b64 cache)")

        return StepResult(True, {
            "generated": len(images),
            "total_slots": len(ai_slots),
            "images": images,
        })

    def post_gate(self, result: StepResult) -> list[str]:
        issues = []
        gen = result.artifact.get("generated", 0)
        total = result.artifact.get("total_slots", 0)
        if total > 0 and gen == 0:
            issues.append("No images were generated despite having AI slots")
        return issues
