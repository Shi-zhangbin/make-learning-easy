#!/usr/bin/env python3
"""Generate a 3x3 sprite sheet via wuyinkeji API."""
import argparse, requests, time, sys, os
from pathlib import Path

SUBMIT_URL = "https://api.wuyinkeji.com/api/async/image_gpt"
DETAIL_URL = "https://api.wuyinkeji.com/api/async/detail"

def generate_sprite(prompt: str, api_key: str, output: str, size: str = "1:1", timeout: int = 180):
    """Submit and poll until sprite is ready."""
    r = requests.post(SUBMIT_URL, json={"prompt": prompt, "size": size, "key": api_key}, timeout=15)
    data = r.json()
    if data.get("code") != 200:
        raise RuntimeError(f"Submit failed: {data.get('msg', '?')}")
    task_id = data["data"]["id"]
    print(f"Task: {task_id}", flush=True)

    wait = 3
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(wait)
        r = requests.get(DETAIL_URL, params={"key": api_key, "id": task_id}, timeout=15)
        resp = r.json()
        status = resp.get("data", {}).get("status", 0)
        print(f"  status={status}", flush=True)
        if status == 2:
            urls = resp.get("data", {}).get("result", [])
            if urls:
                img = requests.get(urls[0], timeout=60)
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                with open(output, "wb") as f:
                    f.write(img.content)
                print(f"Saved: {output} ({len(img.content)} bytes)", flush=True)
                return True
            raise RuntimeError("No result URL")
        elif status == -1:
            raise RuntimeError("Content rejected")
        wait = min(wait * 1.5, 30)
    raise TimeoutError("Generation timed out")

def main():
    p = argparse.ArgumentParser(description="Generate sprite sheet")
    p.add_argument("--prompt", required=True, help="Image description")
    p.add_argument("--key", default=os.environ.get("WUYINKEJI_KEY", ""), help="API key")
    p.add_argument("--out", default="run_sprite.png", help="Output path")
    p.add_argument("--size", default="1:1", help="Image aspect ratio")
    args = p.parse_args()
    if not args.key:
        print("Error: provide --key or set WUYINKEJI_KEY")
        sys.exit(1)
    generate_sprite(args.prompt, args.key, args.out, args.size)

if __name__ == "__main__":
    main()
