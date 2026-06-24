---
name: bilibili-sprite-gen
description: "Generate running sprite characters for Bilibili video progress bars using wuyinkeji async API. Use when generating running animation sprite sheets for video progress bar characters"
---

# Bilibili Sprite Sheet Generator

Generates running character sprites for video progress bars via wuyinkeji API.

## Usage

```bash
python3 skills/bilibili-sprite-gen/scripts/generate_sprite.py \
  --prompt "your description of the character and style" \
  --key "$WUYINKEJI_KEY" \
  --out output.png
```

## Pipeline Integration

Called in T6 step. The script submits a prompt to wuyinkeji API, polls for completion, saves the PNG.
