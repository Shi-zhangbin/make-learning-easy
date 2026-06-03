#!/usr/bin/env python3
"""T5 AI配图批量生成 - 并发3-4张，使用wuyinkeji API"""
import json, os, time, sys, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True)

# === Config ===
API_KEY = "0BgUoOwfbQSLjWARMMx1APtbKu"
PROJECT_DIR = os.path.expanduser(
    "~/Desktop/ascend-pipeline/episodes"
    "/第2期_昇腾部署Qwen3-VL-8B概念讲解"
)
SLOTS_FILE = os.path.join(PROJECT_DIR, "04_PPT大纲", "image_slots.json")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "05_图片素材", "ai")
BATCH_SIZE = 4  # concurrent tasks
POLL_INTERVAL = 5  # seconds between poll attempts
MAX_POLL_RETRIES = 90  # ~7.5 min max per image
MAX_DOWNLOAD_RETRIES = 5

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === API functions ===

def submit_task(prompt, size="16:9"):
    """Submit image generation task, return task_id"""
    data = json.dumps({"key": API_KEY, "prompt": prompt, "size": size}).encode()
    req = urllib.request.Request(
        "https://api.wuyinkeji.com/api/async/image_gpt",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())
        if result.get("code") == 200:
            return result["data"]["id"]
        raise Exception(f"Submit failed: {json.dumps(result, ensure_ascii=False)[:200]}")

def poll_task(task_id, max_retries=MAX_POLL_RETRIES):
    """Poll task status, return image URL when done"""
    for i in range(max_retries):
        url = f"https://api.wuyinkeji.com/api/async/detail?key={API_KEY}&id={task_id}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                if result.get("code") == 200:
                    data = result.get("data", {})
                    status = data.get("status")
                    if status == 2:  # success
                        urls = data.get("result", [])
                        if urls:
                            return urls[0]
                        else:
                            raise Exception("No result URL returned (status=2 but empty result)")
                    elif status == 3:  # content rejected
                        raise Exception("Content rejected (status=3)")
                    # status 0/1 = pending/processing, continue polling
        except urllib.request.HTTPError as e:
            pass  # transient error, retry
        except Exception as e:
            if "Content rejected" in str(e):
                raise  # propagate rejection
            pass  # transient error, retry
        time.sleep(POLL_INTERVAL)
    raise Exception(f"Poll timeout after {max_retries * POLL_INTERVAL}s for task {task_id}")

def download_image(url, filepath):
    """Download image with retries"""
    for i in range(MAX_DOWNLOAD_RETRIES):
        try:
            urllib.request.urlretrieve(url, filepath)
            if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
                return True
        except Exception:
            time.sleep(5)
    return False

def process_one(slot):
    """Process a single image slot - returns (filename, success, msg)"""
    page = slot["page"]
    slot_name = slot["slot"]
    prompt = slot.get("prompt", "")
    size = slot.get("size", "16:9")
    api_size = "16:9"  # all AI images are 16:9

    fname = f"ai_P{page}_{slot_name}.png"
    fpath = os.path.join(OUTPUT_DIR, fname)

    # Skip if exists and valid
    if os.path.exists(fpath) and os.path.getsize(fpath) > 50000:
        return (fname, True, "skipped (exists)")

    try:
        # Submit
        task_id = submit_task(prompt, api_size)
        # Poll
        img_url = poll_task(task_id)
        # Download
        ok = download_image(img_url, fpath)
        if ok:
            kb = os.path.getsize(fpath) // 1024
            return (fname, True, f"OK {kb}KB")
        else:
            return (fname, False, "download failed")
    except Exception as e:
        msg = str(e)[:100]
        return (fname, False, msg)


def main():
    print("=" * 60, flush=True)
    print(f"T5 AI配图批量生成 | {time.strftime('%H:%M:%S')}", flush=True)
    print(f"Key: {API_KEY[:8]}...", flush=True)
    print(f"输出: {OUTPUT_DIR}", flush=True)
    print("=" * 60, flush=True)

    # Load slots
    with open(SLOTS_FILE) as f:
        data = json.load(f)
    slots = data.get("slots", [])
    ai_slots = [s for s in slots if s.get("source") == "ai"]
    print(f"共 {len(ai_slots)} 张AI配图\n", flush=True)

    results = {"success": [], "failed": [], "skipped": []}
    lock = threading.Lock()
    completed = 0

    def on_done(future):
        nonlocal completed
        fname, ok, msg = future.result()
        with lock:
            completed += 1
            if ok and msg.startswith("skipped"):
                results["skipped"].append({"file": fname})
                status = "??"
            elif ok:
                results["success"].append({"file": fname})
                status = "OK"
            else:
                results["failed"].append({"file": fname, "reason": msg})
                status = "FAIL"
            print(f"  [{completed}/{len(ai_slots)}] {fname}: {status} {msg}", flush=True)

    # Process in batches of BATCH_SIZE
    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        futures = []
        for slot in ai_slots:
            future = executor.submit(process_one, slot)
            future.add_done_callback(on_done)
            futures.append(future)
            time.sleep(1)  # slight stagger between submissions

        # Wait for all
        for f in as_completed(futures):
            pass  # callbacks handle reporting

    # Summary
    print(f"\n{'='*60}", flush=True)
    print(f"OK: {len(results['success'])} | FAIL: {len(results['failed'])} | SKIP: {len(results['skipped'])}", flush=True)
    print(f"完成时间: {time.strftime('%H:%M:%S')}", flush=True)

    # Save report
    report_path = os.path.join(OUTPUT_DIR, "t5_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Report: {report_path}", flush=True)

    # Show failed details
    if results["failed"]:
        print(f"\nFAIL details:", flush=True)
        for r in results["failed"]:
            print(f"  {r['file']}: {r['reason']}", flush=True)

if __name__ == "__main__":
    main()
