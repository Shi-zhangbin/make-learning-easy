#!/usr/bin/env python3
"""
pipeline.py — ascend-pipeline 状态编排器 (v3.1)

状态机：
  created -> T0 -> T1 -> T3 -> TTS -> T2 -> T5 -> T6 -> T7 -> T8 -> delivered

      T5(配图) 必须在 T6(Composition) 之前
      T6 生成 composition 时配图已就绪 -> 一步嵌入 base64

状态值: done, pending, in_progress, failed, stalled, revised, skipped

用法:
  python3 scripts/pipeline.py start --topic "PyTorch" --episode "第2期_PyTorch"
  python3 scripts/pipeline.py step --episode 第2期_PyTorch
  python3 scripts/pipeline.py status --episode 第2期_PyTorch
  python3 scripts/pipeline.py repair --episode 第2期_PyTorch
  python3 scripts/pipeline.py heartbeat --episode 第2期_PyTorch
  python3 scripts/pipeline.py verify --episode 第2期_PyTorch  [step=T5]
"""

import argparse, json, os, re, subprocess, sys, glob
from datetime import datetime

BASE = os.path.expanduser("~/Desktop/ascend-pipeline")
STATE_FILE = "pipeline_state.json"

PIPELINE = ["created","T0","T1","T3","TTS","T2","T5","T6","T7","T8","delivered"]

LABELS = {
    "created":"\U0001f3ac 创建", "T0":"\U0001f4da 选题", "T1":"\U0001f4dd 大纲", "T3":"\u270d\ufe0f  口播",
    "TTS":"\U0001f50a TTS", "T2":"\U0001f3a8 分镜", "T5":"\U0001f5bc\ufe0f  配图", "T6":"\U0001f527 Composition",
    "T7":"\U0001f3ac 渲染", "T8":"\U0001f4ac 字幕", "delivered":"\u2705 交付",
}

DEPS = {"T0":[], "T1":["T0"], "T3":["T1"], "TTS":["T3"],
        "T2":["TTS"], "T5":["T2"], "T6":["T5"], "T7":["T6"], "T8":["T7"]}

STALLED_MIN = 15

def spath(ep_dir):
    return os.path.join(ep_dir, STATE_FILE)

def load(ep_dir):
    s = spath(ep_dir)
    if os.path.exists(s):
        with open(s) as f:
            return json.load(f)
    return {"episode": os.path.basename(ep_dir), "steps": {}, "current_step": "created"}

def save(ep_dir, state):
    state["updated_at"] = datetime.now().isoformat()
    with open(spath(ep_dir), "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def mark(ep_dir, step, status, detail=""):
    state = load(ep_dir)
    entry = {"status": status, "detail": detail, "ts": datetime.now().isoformat()}
    if status in ("in_progress",):
        entry["heartbeat_ts"] = datetime.now().isoformat()
    state["steps"][step] = entry
    if status == "done":
        idx = PIPELINE.index(step)
        if idx + 1 < len(PIPELINE):
            state["current_step"] = PIPELINE[idx + 1]
        else:
            state["current_step"] = "delivered"
    elif status == "revised":
        idx = PIPELINE.index(step)
        for s in PIPELINE[idx+1:]:
            if s in state["steps"]:
                del state["steps"][s]
        state["current_step"] = step
    else:
        state["current_step"] = step
    save(ep_dir, state)

def heartbeat(ep_dir, step):
    state = load(ep_dir)
    si = state.get("steps", {}).get(step, {})
    if si.get("status") == "in_progress":
        si["heartbeat_ts"] = datetime.now().isoformat()
        save(ep_dir, state)
        return True
    return False

def check_stalled(state):
    now = datetime.now()
    stalled = []
    for step, si in state.get("steps", {}).items():
        if si.get("status") != "in_progress":
            continue
        hb = si.get("heartbeat_ts", si.get("ts"))
        if not hb:
            continue
        try:
            dt = datetime.fromisoformat(hb)
            idle = (now - dt).total_seconds() / 60
            if idle > STALLED_MIN:
                stalled.append((step, int(idle)))
        except:
            pass
    return stalled

def verify_step(ed, step, quiet=False):
    def _find(relpath):
        for root, dirs, files in os.walk(ed):
            for f in files:
                if f == relpath or os.path.join(root, f).endswith(relpath):
                    return True
        return False
    def _count(pattern):
        return len(glob.glob(os.path.join(ed, pattern)))
    checks = {
        "T0": [("选题报告", lambda: _find("选题研究.md") or os.path.isdir(os.path.join(ed, "00_选题")))],
        "T1": [("知识点大纲", lambda: _find("知识点大纲.md") or os.path.isdir(os.path.join(ed, "01_大纲")))],
        "T3": [("口播稿", lambda: any(os.path.exists(os.path.join(ed, f)) for f in ["口播稿.txt","配音稿.txt","配音稿_分段.txt","narration.txt","02_口播稿/口播稿.txt"]))],
        "TTS": [("timeline.json", lambda: _find("timeline.json")),
                ("音频文件", lambda: _count("audio/*.mp3") > 0 or _count("03_audio/*.mp3") > 0)],
        "T2": [("PPT大纲", lambda: _find("PPT大纲.md") or os.path.isdir(os.path.join(ed, "04_PPT大纲"))),
                ("image_slots.json", lambda: _find("image_slots.json"))],
        "T5": [("配图目录", lambda: _count("images/*") > 0 or _count("05_图片素材/**/*") > 0 or _count("images/*.jpg") > 0)],
                    "T6": [("composition文件", lambda: _count("**/compositions/*.html") >= 3)],
            "T7": [("视频输出", lambda: _count("*.mp4") > 0 or _count("**/*.mp4") > 3)],
        "T8": [("(可选)", lambda: True)],
    }
    results = []
    for label, check_fn in checks.get(step, []):
        ok = check_fn()
        results.append((label, ok))
        if not quiet:
            icon = "\u2705" if ok else "\u274c"
            print(f"  {icon} {label}")
    all_ok = all(ok for _, ok in results)
    return all_ok, results

def can_run(state, step):
    if step in ("created","delivered"):
        return False, "边界步骤"
    si = state.get("steps", {}).get(step, {})
    if si.get("status") == "done":
        return False, f"{step} 已完成"
    if si.get("status") == "skipped":
        return False, f"{step} 已跳过"
    for dep in DEPS.get(step, []):
        di = state.get("steps", {}).get(dep, {}).get("status")
        if di not in ("done", "skipped"):
            return False, f"{dep} 未完成"
    return True, ""

def pending_steps(state):
    result = []
    for s in PIPELINE:
        if s in ("created","delivered"):
            continue
        si = state.get("steps", {}).get(s, {})
        if si.get("status") in ("done","skipped"):
            continue
        deps_met = True
        for d in DEPS.get(s, []):
            di = state.get("steps", {}).get(d, {}).get("status")
            if di not in ("done","skipped"):
                deps_met = False
                break
        if deps_met:
            result.append(s)
    return result

def find_ep(name):
    if os.path.isabs(name) and os.path.isdir(name):
        return os.path.abspath(name)
    for d in [os.path.join(BASE,"episodes",name), os.path.join(BASE,name)]:
        if os.path.isdir(d):
            return d
    return None

# Commands
def cmd_start(args):
    ep = args.episode or f"第{args.number}期_{args.topic}"
    ed = os.path.join(BASE, "episodes", ep)
    if os.path.exists(ed):
        print(f"\u26a0\ufe0f  已存在: {ep}")
        return
    os.makedirs(os.path.join(ed, "compositions"), exist_ok=True)
    os.makedirs(os.path.join(ed, "images"), exist_ok=True)
    os.makedirs(os.path.join(ed, "audio"), exist_ok=True)
    with open(os.path.join(ed, ".design-system"), "w") as f:
        f.write(args.design + "\n")
    with open(os.path.join(ed, "README.md"), "w") as f:
        f.write(f"# {ep}\n\n> {args.topic}\n\n风格: {args.design}\n")
    state = {"episode": ep, "topic": args.topic, "design_style": args.design,
             "steps": {}, "current_step": "created", "created_at": datetime.now().isoformat()}
    save(ed, state)
    mark(ed, "created", "done", args.topic)
    print(f"\n\u2705 {ep}")
    print(f"   \U0001f4cd {ed}")
    print(f"   \U0001f3af {args.topic}")
    print(f"   \U0001f3a8 {args.design}")
    print(f"\n下一步: python3 scripts/pipeline.py step --episode \"{ep}\"")

def cmd_status(args):
    ed = find_ep(args.episode)
    if not ed:
        print(f"\u274c 不存在: {args.episode}"); return
    state = load(ed)
    print(f"\n\U0001f4ca {os.path.basename(ed)}")
    print(f"   \U0001f3af {state.get('topic','?')}  \U0001f3a8 {state.get('design_style','?')}")
    cur = state.get("current_step","?")
    print(f"   \U0001f4cc 当前: {LABELS.get(cur,cur)}")
    stalled = check_stalled(state)
    if stalled:
        print(f"   \u26a0\ufe0f  停滞步骤: {', '.join(f'{s}({m}\u5206\u949f\u65e0\u54cd\u5e94)' for s,m in stalled)}")
        print(f"      (建议: repair --episode \"{os.path.basename(ed)}\")")
    print()
    for s in PIPELINE:
        si = state.get("steps", {}).get(s, {})
        st = si.get("status","")
        detail = si.get("detail","")
        if state.get("current_step") == s and st != "done":
            icon = "\u23f3"
        else:
            icon = {"done":"\u2705","failed":"\u274c","in_progress":"\u23f3","stalled":"\u26a0\ufe0f","revised":"\U0001f504","skipped":"\u2796"}.get(st,"\u2b1c")
        label = LABELS.get(s, s)
        line = f"  {icon} {label}"
        if detail and st not in ("done", ""):
            line += f"  \u2014 {detail}"
        print(line)

def cmd_step(args):
    ed = find_ep(args.episode)
    if not ed:
        print(f"\u274c 不存在: {args.episode}"); return
    state = load(ed)
    step = args.step or state.get("current_step","T0")
    if step in ("created","delivered"):
        candidates = pending_steps(state)
        step = candidates[0] if candidates else "T0"
    ok, reason = can_run(state, step)
    if not ok:
        print(f"\u23ed\ufe0f  {reason}")
        pending = pending_steps(state)
        if pending:
            print(f"   可执行: {[f'{s}({LABELS.get(s,s)})' for s in pending[:3]]}")
        return
    print(f"\n{'#'*60}\n# {LABELS.get(step, step)}\n{'#'*60}")
    executors = {"TTS": lambda: run_tts(ed, state), "T5": lambda: run_t5(ed, state)}
    fn = executors.get(step)
    if fn:
        fn()
    else:
        guides = {
            "T0": ["delegate_task \u7ed9 xuan-ti-yan-jiu-yuan (deepseek-v4-pro)", "\u4ea7\u51fa: \u9009\u9898\u7814\u7a76.md"],
            "T1": ["delegate_task \u7ed9 yanjiuyuan (deepseek-v4-pro)", "\u4ea7\u51fa: \u77e5\u8bc6\u70b9\u5927\u7eb2.md"],
            "T3": ["delegate_task \u7ed9 bianju (MiniMax-M2.7)", "\u4ea7\u51fa: \u914d\u97f3\u7a3f.txt"],
            "T2": ["delegate_task \u7ed9 meishu (MiniMax-M2.7)",
                   f"DESIGN.md: {BASE}/designs/awesome-design-md/design-md/{state.get('design_style','mintlify')}/DESIGN.md",
                   "\u26a0\ufe0f image_slots.json \u5fc5\u987b\u542b filename \u5b57\u6bb5"],

            "T5": ["可跳过: python3 scripts/pipeline.py skip --episode \"<ep>\" --step T5",
                   "  API Key 已配: python3 scripts/pipeline.py step --episode \"<ep>\" --step T5 (自动生成)"],
            "T6": ["delegate_task 给 editor (qwen3.6-plus)",
                   "铁律: 图片从 images/ 目录读取并 base64 嵌入",
                   "  image_slots.json 定义了 filename, T5 已生成到 images/",
                   "  如果 images/ 不存在或为空: T5 被跳过, 用纯文字占位",
                   "  从 images/ 读取 base64:",
                   '  with open(f"images/{fn}", "rb") as f:',
                   "      b64 = base64.b64encode(f.read()).decode()",
                   '  img = f\'<img src="data:image/jpeg;base64,{b64}">\'',
                   "⚠️ 优先 HyperFrames Block, 再 generate_composition.py 兜底",
                   "   context: DESIGN.md + PPT大纲 + images/ + AGENTS.md",
                   "✅ 完成后: python3 scripts/harness.py \"<ep>\" 2"],
            "T7": ["✅ 自动: python3 scripts/pipeline.py verify --episode \"<ep>\"",
                   "  hyperframes render . --fps 15 -o final.mp4",
                   "  ffmpeg + audio merge (见 AGENTS.md §4)"],
            "T8": ["默认跳过: python3 scripts/pipeline.py skip --episode \"<ep>\" --step T8"],
        }
        for g in guides.get(step, []):
            print(f"   \u2022 {g}")
        print(f"\n完成后: python3 scripts/pipeline.py step --episode \"{os.path.basename(ed)}\"")

def cmd_verify(args):
    ed = find_ep(args.episode)
    if not ed:
        print(f"\u274c 不存在: {args.episode}"); return
    state = load(ed)
    target = args.step or state.get("current_step","T0")
    if target and target in PIPELINE:
        print(f"\n\U0001f50d \u6821\u9a8c {LABELS.get(target, target)}")
        ok, results = verify_step(ed, target)
        print(f"\n{'\u2705 \u5168\u90e8\u901a\u8fc7' if ok else '\u274c \u90e8\u5206\u672a\u901a\u8fc7'}")
        return
    print(f"\n\U0001f50d \u5168\u6b65\u9aa4\u6821\u9a8c")
    all_good = True
    for s in PIPELINE:
        si = state.get("steps", {}).get(s, {})
        if si.get("status") != "done":
            continue
        ok, _ = verify_step(ed, s, quiet=True)
        print(f"  {LABELS.get(s,s)}: {'\u2705' if ok else '\u274c'}")
        if not ok: all_good = False
    print(f"\n{'\U0001f389 \u5168\u90e8\u5b8c\u6574' if all_good else '\u274c \u90e8\u5206\u7f3a\u5931'}")

def cmd_heartbeat(args):
    ed = find_ep(args.episode)
    if not ed:
        print(f"\u274c \u4e0d\u5b58\u5728: {args.episode}"); return
    state = load(ed)
    cur = state.get("current_step", "")
    if heartbeat(ed, cur):
        print(f"\u2705 {cur} \u5fc3\u8df3\u5df2\u66f4\u65b0")
    else:
        print(f"\u2139\ufe0f  {cur} \u4e0d\u5728\u8fd0\u884c\u4e2d\uff0c\u65e0\u9700\u5fc3\u8df3")

def cmd_repair(args):
    ed = find_ep(args.episode)
    if not ed:
        print(f"\u274c \u4e0d\u5b58\u5728: {args.episode}"); return
    state = load(ed)
    changed = False
    stalled = check_stalled(state)
    if stalled:
        print(f"\n\u26a0\ufe0f  \u68c0\u6d4b\u5230\u505c\u6ede\u6b65\u9aa4:")
        for st, mins in stalled:
            print(f"   {st}: {mins}\u5206\u949f\u65e0\u54cd\u5e94")
    for step in PIPELINE:
        if step in ("created","delivered"):
            continue
        si = state.get("steps", {}).get(step, {})
        if si.get("status") in ("done","skipped"):
            continue
        step_idx = PIPELINE.index(step)
        deps_met = all(
            state.get("steps", {}).get(p, {}).get("status") in ("done","skipped")
            for p in PIPELINE[:step_idx] if p != "created"
        ) if step_idx >= 0 else True
        if deps_met:
            mark(ed, step, "done", "(\u5df2\u4fee\u590d)")
            print(f"  \u2705 {step} \u2192 done")
            changed = True
    if not changed:
        print("  \u2139\ufe0f  \u72b6\u6001\u4e00\u81f4")

def cmd_skip(args):
    ed = find_ep(args.episode)
    if not ed:
        print(f"\u274c \u4e0d\u5b58\u5728: {args.episode}"); return
    step = args.step
    if step not in PIPELINE:
        print(f"\u274c \u672a\u77e5\u6b65\u9aa4: {step}"); return
    mark(ed, step, "skipped", "\u624b\u52a8\u8df3\u8fc7")
    print(f"  \u2796 {step} \u2192 skipped")

def run_tts(ed, state):
    for name in ["\u914d\u97f3\u7a3f_\u5206\u6bb5.txt","\u914d\u97f3\u7a3f.txt","narration.txt","02_\u53e3\u64ad\u7a3f/\u53e3\u64ad\u7a3f.txt"]:
        p = os.path.join(ed, name)
        if os.path.exists(p):
            sp = p; break
    else:
        print("\u274c \u672a\u627e\u5230\u53e3\u64ad\u7a3f"); return
    print(f"   \u53e3\u64ad\u7a3f: {os.path.relpath(sp, ed)}")
    subprocess.run([sys.executable, os.path.join(BASE,"scripts","tts_to_durations.py"),
                    "--input", sp, "--parse-only"], check=False)
    r = subprocess.run([sys.executable, os.path.join(BASE,"scripts","tts_to_durations.py"),
                        "--input", sp, "--audio-dir", os.path.join(ed,"audio"),
                        "--generate", "--out-json", os.path.join(ed,"timeline.json")],
                       check=False)
    mark(ed, "TTS", "done" if r.returncode == 0 else "failed", "TTS \u751f\u6210+\u5206\u6bb5" if r.returncode == 0 else "TTS \u5931\u8d25")

def run_t5(ed, state):
    """T5: 按 image_slots.json 生成配图到 images/"""
    script = os.path.join(BASE, "scripts", "generate_images.py")
    if not os.path.exists(script):
        print(f"\u274c \u7f3a {script}")
        return
    # dry-run
    r = subprocess.run([sys.executable, script, ed, "--dry-run"], check=False)
    if r.returncode != 0:
        mark(ed, "T5", "failed", "dry-run\u5931\u8d25")
        return
    # API Key check
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("\n\u26a0\ufe0f  OPENAI_API_KEY \u672a\u8bbe\u7f6e")
        print("   A) export OPENAI_API_KEY=sk-xxx \u540e\u91cd\u8bd5")
        print(f"   B) python3 scripts/pipeline.py skip --episode \"{os.path.basename(ed)}\" --step T5")
        return
    # \u751f\u6210
    r = subprocess.run([sys.executable, script, ed], check=False)
    if r.returncode == 0:
        mark(ed, "T5", "done", "\u914d\u56fe\u751f\u6210\u5b8c\u6210")
        print("\n\u2705 T5 \u5b8c\u6210")
    else:
        mark(ed, "T5", "failed", "\u914d\u56fe\u751f\u6210\u5931\u8d25")
def main():
    p = argparse.ArgumentParser(description="ascend-pipeline \u7ba1\u7ebf\u7f16\u6392\u5668 (v3.1)")
    s = p.add_subparsers(dest="cmd", required=True)
    for name, opts in [
        ("start", {"topic": True, "episode": False, "number": "1", "design": "mintlify"}),
    ]:
        sp = s.add_parser("start"); sp.add_argument("--topic", required=True)
        sp.add_argument("--episode"); sp.add_argument("--number", default="1"); sp.add_argument("--design", default="mintlify")

    sp = s.add_parser("step")
    sp.add_argument("--episode", required=True)
    sp.add_argument("--step", choices=[x for x in PIPELINE if x not in ("created","delivered")])

    sp = s.add_parser("status"); sp.add_argument("--episode", required=True)
    sp = s.add_parser("repair"); sp.add_argument("--episode", required=True)

    sp = s.add_parser("skip")
    sp.add_argument("--episode", required=True)
    sp.add_argument("--step", choices=[x for x in PIPELINE if x not in ("created","delivered")], required=True)

    sp = s.add_parser("verify")
    sp.add_argument("--episode", required=True)
    sp.add_argument("--step", choices=[x for x in PIPELINE if x not in ("created","delivered")])

    sp = s.add_parser("heartbeat"); sp.add_argument("--episode", required=True)

    args = p.parse_args()
    dispatch = {"start":cmd_start,"step":cmd_step,"status":cmd_status,
                "repair":cmd_repair,"skip":cmd_skip,"verify":cmd_verify,"heartbeat":cmd_heartbeat}
    dispatch[args.cmd](args)

if __name__ == "__main__":
    main()
