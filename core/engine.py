"""
core/engine.py — Pipeline orchestration engine

Manages step state, dispatch, and dependencies.
Entry point: core/engine.py or go.sh
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime
from core.config import EPISODES_DIR, PRESETS_DIR, FILE_NAMES, validate_episode_name, parse_episode_name, get_agent_default, resolve_episode_path
from core.designs.base import load_preset, list_presets

# ── Step registry ──
STEPS = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]

# Dependencies: step -> list of step names that must be done first
DEPS = {
    "T0": [],
    "T1": ["T0"],
    "T2": ["T1"],
    "T3": ["T2"],
    "T4": ["T3"],
    "T5": ["T4"],
    "T6": ["T5"],
    "T7": ["T6"],
    "T8": ["T7"],
}

STEP_LABELS = {
    "T0": "选题研究", "T1": "知识点大纲", "T2": "口播稿",
    "T3": "配音+字幕", "T4": "分镜设计", "T5": "配图生成",
    "T6": "Composition", "T7": "渲染+后期", "T8": "字幕（可选）",
}


def get_episode_dir(name: str) -> str:
    """Resolve episode name to directory path."""
    if os.path.isabs(name) and os.path.isdir(name):
        return name
    # Try episodes/ subdirectory
    path = os.path.join(EPISODES_DIR, name)
    if os.path.isdir(path):
        return path
    # Try direct path
    if os.path.isdir(name):
        return name
    # Try episodes/NAME relative to cwd
    cwd_path = os.path.join(os.getcwd(), "episodes", name)
    if os.path.isdir(cwd_path):
        return cwd_path
    raise FileNotFoundError(f"Episode not found: {name}")


def load_state(episode_dir: str) -> dict:
    """Load pipeline state from episode directory."""
    state_path = resolve_episode_path(episode_dir, "pipeline_state")
    if os.path.exists(state_path):
        with open(state_path) as f:
            return json.load(f)
    return {
        "episode": os.path.basename(episode_dir),
        "current_step": "T0",
        "steps": {},
        "design_style": "bilibili",
        "created_at": datetime.now().isoformat(),
    }


def save_state(episode_dir: str, state: dict):
    """Save pipeline state."""
    state["updated_at"] = datetime.now().isoformat()
    state_path = os.path.join(episode_dir, FILE_NAMES["pipeline_state"])
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    # Clean up old-format state file if it exists
    old_path = os.path.join(episode_dir, "pipeline_state.json")
    if old_path != state_path and os.path.exists(old_path):
        os.remove(old_path)


def can_run_step(state: dict, step: str) -> tuple[bool, str]:
    """Check if a step can run given current state."""
    if step not in STEPS:
        return False, f"Unknown step: {step}"
    si = state.get("steps", {}).get(step, {})
    if si.get("status") in ("done", "skipped"):
        return False, f"{step} already completed/skipped"
    for dep in DEPS.get(step, []):
        di = state.get("steps", {}).get(dep, {}).get("status")
        if di not in ("done", "skipped"):
            return False, f"Dependency not met: {dep} ({di or 'not started'})"
    return True, ""


def run_step(episode_dir: str, step: str, design: dict | None = None,
             tone: dict | None = None):
    """Execute a single pipeline step."""
    from core.designs.base import load_preset
    from core.steps.base import StepHandler

    state = load_state(episode_dir)
    ok, reason = can_run_step(state, step)
    if not ok:
        print(f"  ❌ {reason}")
        return False

    # Load the step handler
    handler = _get_handler(step, episode_dir, design, tone)
    if not handler:
        print(f"  ❌ No handler implemented for {step}")
        print(f"     This step must be done manually via agent delegation.")
        return False

    # Mark in_progress
    state["steps"][step] = {
        "status": "in_progress",
        "ts": datetime.now().isoformat(),
        "heartbeat_ts": datetime.now().isoformat(),
    }
    state["current_step"] = step
    save_state(episode_dir, state)

    print(f"\n{'='*60}")
    print(f"  {step}: {STEP_LABELS.get(step, step)}")
    print(f"{'='*60}")

    # Run
    result = handler.run()

    if result:
        # Run post-execution gate
        from core.gates.gate_master import run_gate
        gate = run_gate(step, episode_dir)
        
        if not gate:
            # Gate failed — write feedback file, don't mark done
            fb_path = os.path.join(episode_dir, "gate-feedback.json")
            with open(fb_path, "w", encoding="utf-8") as f:
                json.dump({
                    "issues": gate.issues,
                    "feedback_target": gate.feedback_target,
                    "step": step,
                    "timestamp": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)
            state["steps"][step] = {
                "status": "failed",
                "ts": datetime.now().isoformat(),
                "detail": {"gate_failed": True, "issues": gate.issues, "feedback_target": gate.feedback_target},
            }
            state["current_step"] = step
            save_state(episode_dir, state)
            print(f"\n  ❌ {step} 门禁未通过")
            print(f'\n  → 请修改后重试: bash go.sh run --episode \"{os.path.basename(episode_dir)}\" --step {step}')
            return False

        # Success — gate passed, clean up old feedback
        fb_path = os.path.join(episode_dir, "gate-feedback.json")
        if os.path.exists(fb_path):
            os.remove(fb_path)
        state["steps"][step] = {
            "status": "done",
            "ts": datetime.now().isoformat(),
            "detail": result.artifact,
        }
        # Advance to next pending step
        next_step = _next_pending(state)
        state["current_step"] = next_step if next_step else step
        save_state(episode_dir, state)
        print(f"\n  ✅ {step} 通过门禁")
        if next_step:
            print(f"  → Next: {next_step} ({STEP_LABELS.get(next_step, '')})")
        return True
    else:
        # Failed
        state["steps"][step] = {
            "status": "failed",
            "ts": datetime.now().isoformat(),
            "detail": result.errors,
        }
        state["current_step"] = step
        save_state(episode_dir, state)
        print(f"\n  ❌ {step} failed:")
        for err in result.errors:
            print(f"     - {err}")
        return False


def _get_handler(step: str, episode_dir: str, design: dict | None,
                 tone: dict | None = None):
    """Get the StepHandler for a given step, or None if manual."""
    from core.steps.tts import TTSHandler
    from core.steps.t5_images import ImageHandler
    from core.steps.t6_compositions import CompositionHandler
    from core.steps.t7_render import RenderHandler
    from core.agent_steps import TopicResearchHandler, OutlineHandler, ScriptHandler, StoryboardHandler

    t0_topic = ""
    for fname in [FILE_NAMES["pipeline_state"], "pipeline_state.json"]:
        state_path = os.path.join(episode_dir, fname)
        if os.path.exists(state_path):
            import json
            with open(state_path) as f:
                s = json.load(f)
            t0_topic = s.get("topic", "")
            break

    handlers = {
        "T0": lambda ed, d: TopicResearchHandler(ed, d, t0_topic, tone),
        "T1": lambda ed, d: OutlineHandler(ed, d, tone=tone),
        "T2": lambda ed, d: ScriptHandler(ed, d, tone=tone),
        "T3": lambda ed, d: TTSHandler(ed, d, tone=tone),
        "T4": lambda ed, d: StoryboardHandler(ed, d, tone=tone),
        "T5": lambda ed, d: ImageHandler(ed, d, tone=tone),
        "T6": lambda ed, d: CompositionHandler(ed, d, tone=tone),
        "T7": lambda ed, d: RenderHandler(ed, d, tone=tone),
    }
    cls = handlers.get(step)
    if cls:
        return cls(episode_dir, design)
    return None


def _next_pending(state: dict) -> str | None:
    """Find the next step that can run."""
    for step in STEPS:
        si = state.get("steps", {}).get(step, {})
        if si.get("status") in ("done", "skipped"):
            continue
        deps_ok = all(
            state.get("steps", {}).get(d, {}).get("status") in ("done", "skipped")
            for d in DEPS.get(step, [])
        )
        if deps_ok:
            return step
    return None


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def cmd_status(args):
    episode_dir = get_episode_dir(args.episode)
    state = load_state(episode_dir)

    print(f"\n📊 {state.get('episode', os.path.basename(episode_dir))}")
    print(f"   风格: {state.get('design_style', 'bilibili')}")
    print(f"   话风: {state.get('tone_style', 'talk-show')}")
    print(f"   当前: {state.get('current_step', '?')} ({STEP_LABELS.get(state['current_step'], '')})")
    print()

    for step in STEPS:
        si = state.get("steps", {}).get(step, {})
        st = si.get("status", "")
        label = STEP_LABELS.get(step, step)

        if st == "done":
            icon = "✅"
        elif st == "in_progress":
            icon = "⏳"
        elif st == "failed":
            icon = "❌"
        elif st == "skipped":
            icon = "⏭"
        else:
            icon = "⬜"

        if state.get("current_step") == step and st != "done":
            icon = "▶️"

        print(f"  {icon} {step:4s} {label}")


def cmd_run(args):
    episode_dir = get_episode_dir(args.episode)
    state = load_state(episode_dir)

    # Determine which step to run
    step = args.step or state.get("current_step", "T0")

    # Load design
    style = state.get("design_style", "bilibili")
    try:
        design = load_preset(style)
    except FileNotFoundError:
        print(f"  ⚠️  Design preset '{style}' not found, using default")
        design = load_preset("bilibili")

    # Load tone
    from core.tones.base import load_tone
    tone_name = state.get("tone_style", "talk-show")
    try:
        tone = load_tone(tone_name)
    except FileNotFoundError:
        print(f"  ⚠️  Tone preset '{tone_name}' not found, using default")
        tone = load_tone("talk-show")

    run_step(episode_dir, step, design, tone)



def write_agent_json(episode_dir: str, agent: str, topic: str, style: str,
                     tone_style: str = "talk-show"):
    """Write .agent.json metadata file for the episode."""
    import json
    from datetime import datetime
    from core.config import FILE_NAMES
    meta = {
        "agent": agent,
        "engine": "core",
        "created": datetime.now().isoformat(),
        "topic": topic,
        "design_style": style,
        "tone_style": tone_style,
    }
    path = os.path.join(episode_dir, FILE_NAMES["agent_info"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def cmd_init(args):
    """Initialize a new episode project."""
    name = args.name
    topic = args.topic or name
    style = args.style or "bilibili"
    tone_style = getattr(args, "tone", "talk-show")

    # Validate naming convention
    valid, err = validate_episode_name(name)
    if not valid:
        print(f"  ❌ {err}")
        return

    # Create episode directory
    episode_dir = os.path.join(EPISODES_DIR, name)
    if os.path.exists(episode_dir):
        print(f"  ❌ Episode already exists: {episode_dir}")
        return

    # Parse name parts
    parts = parse_episode_name(name)

    # Create episode subdirectories (step handlers create their own dirs on-demand)
    os.makedirs(os.path.join(episode_dir, "compositions"), exist_ok=True)

    # Verify design preset exists
    try:
        load_preset(style)
    except FileNotFoundError:
        print(f"  ⚠️  Design '{style}' not found. Available:")
        for p in list_presets():
            print(f"     - {p['name']}: {p['display_name']}")
        style = "bilibili"

    # Verify tone preset exists
    from core.tones.base import load_tone
    try:
        load_tone(tone_style)
    except FileNotFoundError:
        print(f"  ⚠️  Tone '{tone_style}' not found. Available:")
        from core.tones.base import list_tones
        for t in list_tones():
            print(f"     - {t['name']}: {t['display_name']}")
        tone_style = "talk-show"

    # Write initial state
    sprite_style = getattr(args, "sprite_style", "") or "boy"
    state = {
        "episode": name,
        "topic": topic,
        "agent": parts.get("agent") or get_agent_default(),
        "current_step": "T0",
        "steps": {},
        "design_style": style,
        "tone_style": tone_style,
        "sprite_style": sprite_style,
        "created_at": datetime.now().isoformat(),
    }
    save_state(episode_dir, state)
    write_agent_json(episode_dir, parts.get("agent") or get_agent_default(), topic, style, tone_style)

    print(f"\n  ✅ Created: {name}")
    print(f"     📁 {episode_dir}")
    print(f"     🎨 {style}")
    print(f"     🎙️ {tone_style}")
    print(f"     🏃 {sprite_style}")
    print(f"     → Next: python3 -m core.engine run --episode \"{name}\"")


def cmd_list(args):
    """List all episodes."""
    if not os.path.isdir(EPISODES_DIR):
        print("  No episodes directory")
        return
    episodes = sorted(os.listdir(EPISODES_DIR))
    for ep in episodes:
        ep_dir = os.path.join(EPISODES_DIR, ep)
        if os.path.isdir(ep_dir):
            state = load_state(ep_dir)
            step = state.get("current_step", "?")
            style = state.get("design_style", "?")
            tone_s = state.get("tone_style", "?")
            agent = state.get("agent", "-")
            print(f"  {ep:45s} {step:4s} 🎨{style:12s} 🎙️{tone_s:16s} 🤖{agent}")



def cmd_create(args):
    """Create a new episode and run the full pipeline automatically."""
    from core.designs.base import load_preset

    name = args.name
    topic = args.topic
    style = args.style or "bilibili"
    tone_style = getattr(args, "tone", "talk-show")

    # Validate naming convention
    valid, err = validate_episode_name(name)
    if not valid:
        print(f"  ❌ {err}")
        return

    parts = parse_episode_name(name)

    # Step 1: init project
    print(f"\n{'='*60}")
    print(f"  创建新项目: {name}")
    print(f"  主题: {topic}")
    print(f"  风格: {style}  |  话风: {tone_style}")
    print(f"{'='*60}\n")

    episode_dir = os.path.join(EPISODES_DIR, name)
    if os.path.exists(episode_dir):
        print(f"  ⚠️  项目已存在，将追加内容")
        # Refresh .agent.json if not exists
        agent_path = os.path.join(episode_dir, FILE_NAMES["agent_info"])
        if not os.path.exists(agent_path):
            write_agent_json(episode_dir, parts.get("agent") or get_agent_default(), topic, style, tone_style)
    else:
        os.makedirs(os.path.join(episode_dir, "audio"), exist_ok=True)
        os.makedirs(os.path.join(episode_dir, FILE_NAMES["images_dir"]), exist_ok=True)
        os.makedirs(os.path.join(episode_dir, "compositions"), exist_ok=True)
        os.makedirs(os.path.join(episode_dir, "成品"), exist_ok=True)

        # Write topic to README
        with open(os.path.join(episode_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\n{topic}\n")

        # Init state
        sprite_style = getattr(args, "sprite_style", "") or "boy"
        state = {
            "episode": name,
            "topic": topic,
            "current_step": "T0",
            "steps": {},
            "design_style": style,
            "tone_style": tone_style,
            "sprite_style": sprite_style,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        save_state(episode_dir, state)
        write_agent_json(episode_dir, parts.get("agent") or get_agent_default(), topic, style, tone_style)

    # Load design preset
    try:
        design = load_preset(style)
    except FileNotFoundError:
        print(f"  ⚠️  设计预设 {style} 不存在，使用 bilibili")
        design = load_preset("bilibili")
        style = "bilibili"

    # Load tone preset
    from core.tones.base import load_tone
    try:
        tone = load_tone(tone_style)
    except FileNotFoundError:
        print(f"  ⚠️  话风 {tone_style} 不存在，使用默认 talk-show")
        tone = load_tone("talk-show")
        tone_style = "talk-show"

    if not args.auto:
        print(f"\n  项目已创建。运行: bash go.sh run --episode \"{name}\"")
        return

    # Step 2: Run all steps automatically
    steps_to_run = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7"]

    for step in steps_to_run:
        state = load_state(episode_dir)
        ok, reason = can_run_step(state, step)
        if not ok:
            print(f"\n  ⏭  {step}: {reason}")
            continue

        print(f"\n{'='*50}")
        print(f"  ▶️  步骤 {step}: {STEP_LABELS.get(step, step)}")
        print(f"{'='*50}")

        # Get handler with topic context for T0
        from core.steps.base import StepHandler
        from core.agent_steps import TopicResearchHandler, OutlineHandler, ScriptHandler, StoryboardHandler
        from core.steps.tts import TTSHandler
        from core.steps.t5_images import ImageHandler
        from core.steps.t6_compositions import CompositionHandler
        from core.steps.t7_render import RenderHandler
        from core.agent_steps import AuditHandler
        handler = None
        
        if step == "T0":
            handler = TopicResearchHandler(episode_dir, design, topic, tone)
        else:
            handlers_map = {
                "T1": lambda ed, d: OutlineHandler(ed, d, tone=tone),
                "T2": lambda ed, d: ScriptHandler(ed, d, tone=tone),
                "T3": lambda ed, d: TTSHandler(ed, d, tone=tone),
                "T4": lambda ed, d: StoryboardHandler(ed, d, tone=tone),
                "T5": lambda ed, d: ImageHandler(ed, d, tone=tone),
                "T6": lambda ed, d: CompositionHandler(ed, d, tone=tone),
                "T7": lambda ed, d: RenderHandler(ed, d, tone=tone),
            }
            cls = handlers_map.get(step)
            if cls:
                handler = cls(episode_dir, design)

        if not handler:
            print(f"  ❌ 没有 {step} 的执行器")
            continue
        
        # Mark in_progress
        state["steps"][step] = {
            "status": "in_progress",
            "ts": __import__("datetime").datetime.now().isoformat(),
            "heartbeat_ts": __import__("datetime").datetime.now().isoformat(),
        }
        state["current_step"] = step
        save_state(episode_dir, state)
        
        # Run
        result = handler.run()
        
        if result:
            state = load_state(episode_dir)
            state["steps"][step] = {
                "status": "done",
                "ts": __import__("datetime").datetime.now().isoformat(),
                "detail": {k: str(v)[:100] for k, v in result.artifact.items()}
            }
            state["current_step"] = step
            save_state(episode_dir, state)
            print(f"  ✅ {step} 完成")
            
            # Optional: run audit after T2
            if step in ("T3", "T2"):
                try:
                    audit = AuditHandler(episode_dir, design)
                    audit_r = audit.run()
                    if audit_r.errors:
                        print(f"  ⚠️  审核发现问题，请查看 {episode_dir}/审核报告.md")
                    else:
                        print(f"  ✅ 内容审核通过")
                except Exception as e:
                    print(f"  ⚠️  审核跳过: {e}")
        else:
            state = load_state(episode_dir)
            state["steps"][step] = {
                "status": "failed",
                "ts": __import__("datetime").datetime.now().isoformat(),
                "detail": result.errors,
            }
            save_state(episode_dir, state)
            print(f"  ❌ {step} 失败:")
            for e in result.errors:
                print(f"     - {e}")
            print(f"\n  管线停在 {step}。修复后运行: bash go.sh run --episode \"{name}\" --step {step}")
            return
    
    parts = parse_episode_name(name)
    _final = FILE_NAMES["final_video"] if not parts.get("legacy") else "成品/final.mp4"
    print(f"\n{'='*60}")
    print(f"  🎉 {name} 完成!")
    print(f"  📁 {episode_dir}/{_final}")
    print(f"{'='*60}")

def cmd_designs(args):
    """List available design presets."""
    print("\n  Available design presets:")
    for p in list_presets():
        print(f"     {p['name']:15s} {p['display_name']}")
    print()


def cmd_tones(args):
    """List available tone presets."""
    from core.tones.base import list_tones
    print("\n  Available tone presets:")
    for t in list_tones():
        print(f"     {t['name']:20s} {t['display_name']}")
    print()


def main():
    import argparse
    p = argparse.ArgumentParser(description="Make Learning Easy Pipeline")
    s = p.add_subparsers(dest="cmd", required=True)

    sp = s.add_parser("init")
    sp.add_argument("name", help="Episode name")
    sp.add_argument("--topic", help="Topic description")
    sp.add_argument("--style", default="bilibili", help="Design preset (visual style)")
    sp.add_argument("--tone", default="talk-show", help="Tone preset (narration voice)")
    sp.add_argument("--sprite-style", default="", help='Runner sprite style (boy/dino/walk/cycle/skateboard/jump/moonwalk/dance/fly)')

    sp = s.add_parser("run")
    sp.add_argument("--episode", required=True)
    sp.add_argument("--step", choices=STEPS)

    sp = s.add_parser("status")
    sp.add_argument("--episode", required=True)

    sp = s.add_parser("list")
    sp = s.add_parser("designs")
    sp = s.add_parser("tones")

    sp = s.add_parser("create")
    sp.add_argument("name", help='Episode name (e.g. 2026-06-27_什么是API_[Codex])')
    sp.add_argument("--topic", required=True, help="Topic description")
    sp.add_argument("--style", default="bilibili", help="Design preset (visual style)")
    sp.add_argument("--tone", default="talk-show", help="Tone preset (narration voice)")
    sp.add_argument("--sprite-style", default="", help='Runner sprite style (boy/dino/walk/cycle/skateboard/jump/moonwalk/dance/fly)')
    sp.add_argument("--auto", action="store_true", default=True, help="Auto-run all steps")

    args = p.parse_args()

    dispatch = {
        "init": cmd_init,
        "run": cmd_run,
        "status": cmd_status,
        "list": cmd_list,
        "designs": cmd_designs,
        "tones": cmd_tones,
        "create": cmd_create,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
