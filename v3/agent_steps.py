"""
v3/agent_steps.py — Hermes agent-driven steps (T0, T1, T3, T2)

Each step delegates to a specific hermes profile/agent to generate
content. Uses `hermes -p {profile} -z "{task}"` in non-interactive mode.
"""
import subprocess, json, os
from v3.steps.base import StepHandler, StepResult


def _hermes_call(profile: str, prompt: str, timeout: int = 300) -> str:
    """Call hermes agent with a profile and task prompt. Returns response text."""
    r = subprocess.run(
        ["hermes", "-p", profile, "-z", prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"hermes {profile} failed: {r.stderr[:500]}")
    return r.stdout


class TopicResearchHandler(StepHandler):
    """T0: Research and write topic study report."""
    name = "T0"
    description = "Research topic and write study report"

    def __init__(self, episode_dir: str, design: dict = None,
                 topic: str = ""):
        super().__init__(episode_dir, design)
        self.topic = topic

    def execute(self) -> StepResult:
        topic = self.topic
        if not topic:
            # Read from README or state
            readme = self.episode_dir / "README.md"
            if readme.exists():
                with open(readme) as f:
                    topic = f.read().strip()
        if not topic:
            return StepResult(False, errors=["No topic specified"])

        prompt = f"""你是一个专业的教育视频选题研究员。请针对以下主题，写一份完整的选题研究报告：
主题：{topic}

请包含：
1. 选题背景和意义
2. 目标受众分析
3. 核心知识点清单（5-8个关键概念）
4. 适合用视频呈现的类比/比喻
5. 推荐的讲解路径/章节划分
6. 常见误区/踩坑点

格式：纯文字 Markdown，不要 ## 标记（避免被 TTS 读成"井号"）"""

        print(f"  🤖 委托 xuan-ti-yan-jiu-yuan 研究选题...")
        response = _hermes_call("xuan-ti-yan-jiu-yuan", prompt, timeout=600)

        out_path = self.episode_dir / "选题研究报告.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"  ✅ 选题研究报告 → {out_path.name}")

        return StepResult(True, {"report": response, "path": str(out_path)})


class OutlineHandler(StepHandler):
    """T1: Write knowledge outline."""
    name = "T1"
    description = "Write knowledge outline based on topic research"

    def execute(self) -> StepResult:
        # Read topic report
        report_path = self.episode_dir / "选题研究报告.md"
        if not report_path.exists():
            return StepResult(False, errors=["No 选题研究报告.md found. Run T0 first."])
        with open(report_path, encoding="utf-8") as f:
            report = f.read()

        prompt = f"""你是一个技术教育内容专家。请根据以下选题研究报告，写一份结构化的知识点大纲。

选题研究报告：
{report[:3000]}

请输出知识点大纲，要求：
1. 每个知识点有清晰的定义
2. 包含代码示例点（如果有代码）
3. 标注容易出错的地方
4. 包含建议的配图说明
5. 适合制作成每页约10-15秒讲解的短视频

格式要求：纯文字，不要 ## ** 等标记"""

        print(f"  🤖 委托 yanjiuyuan 编写知识点大纲...")
        response = _hermes_call("yanjiuyuan", prompt, timeout=600)

        out_path = self.episode_dir / "知识点大纲.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"  ✅ 知识点大纲 → {out_path.name}")

        return StepResult(True, {"outline": response, "path": str(out_path)})


class ScriptHandler(StepHandler):
    """T3: Write narration script."""
    name = "T3"
    description = "Write narration/script based on outline"

    def execute(self) -> StepResult:
        outline_path = self.episode_dir / "知识点大纲.md"
        if not outline_path.exists():
            return StepResult(False, errors=["No 知识点大纲.md found. Run T1 first."])
        with open(outline_path, encoding="utf-8") as f:
            outline = f.read()

        prompt = f"""你是一个专业的教育视频编剧。请根据以下知识点大纲，写一份口播稿。

知识点大纲：
{outline[:3000]}

格式要求：
1. 纯文字，不要 ## ** `` 等任何标记
2. 自然口语化的表达
3. 用 --- P1 标题 (时长) --- 格式分段

每段格式示例：
--- P1 开场介绍 (60s) ---
各位同学好，今天我们来学习一个重要的概念...

--- P2 核心概念 (90s) ---
这个概念的要点是...

请按以下结构组织：
- P1: 开场/引入（约60秒）
- P2-P?：核心知识点讲解（每个约60-90秒）
- 最后一段：总结/下期预告（约30秒）

注意：
❌ 禁止 ## ** 标记
✅ 纯文字，字数控制在每段对应标注的时长"""

        print(f"  🤖 委托 bianju 编写口播稿...")
        response = _hermes_call("bianju", prompt, timeout=600)

        out_path = self.episode_dir / "配音稿_分段.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"  ✅ 口播稿 → {out_path.name}")

        return StepResult(True, {"script": response, "path": str(out_path)})


class StoryboardHandler(StepHandler):
    """T2: Design PPT outline + timeline + image_slots."""
    name = "T2"
    description = "Design PPT outline, timeline and image slots"

    def execute(self) -> StepResult:
        script_path = self.episode_dir / "配音稿_分段.txt"
        if not script_path.exists():
            return StepResult(False, errors=["No 配音稿_分段.txt found. Run T3 first."])
        with open(script_path, encoding="utf-8") as f:
            script = f.read()

        # Check if timeline.json exists (from TTS)
        tl_path = self.episode_dir / "timeline.json"
        timeline_info = ""
        if tl_path.exists():
            with open(tl_path) as f:
                tl = json.load(f)
            timeline_info = f"总时长：{tl.get('total_duration', 0)}秒\n"
            for s in tl.get("slides", []):
                timeline_info += f"  P{s.get('page','?')}: {s.get('duration',0)}秒\n"

        style_name = self.design.get("display_name", "Claude暖色人文")

        prompt = f"""你是一个专业的教育视频美术指导。请根据以下口播稿和TTS时长，完成视频的分镜设计。

口播稿：
{script[:4000]}

TTS实测时长信息：
{timeline_info}

设计风格：{style_name}

请输出三样东西：

【第一部分：PPT大纲.md】
每页包含：
- 页号
- 布局类型（从以下选择：hero封面 / concept概念讲解 / flipped翻转布局 / comparison对比 / code_block代码展示 / flowchart流程图 / card_grid卡片网格 / quote引用 / section_divider过渡页 / outro结尾）
- 标题
- badge标签文字
- 2-4个要点卡片（每个卡片含标题+说明文字）
- 配图需求说明

【第二部分：image_slots.json】
每页配图需求，格式为JSON数组，每个元素包含：
- page: 页号
- slot: "main"(主图) / "analogy"(类比图) / "decoration"(装饰)
- source: "ai"(需要AI生成)
- prompt: 配图描述（用于AI生成或图片搜索）
- size: "16:9"
- filename: "p{页码}_{slot名}.jpg"

【第三部分：布局轮换要求】
相邻页布局不能重复。至少使用4种不同布局。

输出格式：纯文字，不要 ## ** 标记。
JSON部分用 ```json ``` 包裹。"""

        print(f"  🤖 委托 meishu 设计分镜方案...")
        response = _hermes_call("meishu", prompt, timeout=900)

        # Write PPT outline
        out_path = self.episode_dir / "PPT大纲.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"  ✅ PPT大纲 → {out_path.name}")

        # Try to extract image_slots.json from response
        image_slots = []
        if "```json" in response:
            json_part = response.split("```json")[1].split("```")[0].strip()
            try:
                image_slots = json.loads(json_part)
                if isinstance(image_slots, dict) and "slots" in image_slots:
                    image_slots = image_slots["slots"]
                slots_path = self.episode_dir / "image_slots.json"
                with open(slots_path, "w", encoding="utf-8") as f:
                    json.dump({"slots": image_slots}, f, ensure_ascii=False, indent=2)
                print(f"  ✅ image_slots.json → {slots_path.name} ({len(image_slots)} slots)")
            except json.JSONDecodeError:
                print(f"  ⚠️  image_slots.json 提取失败，需要手动创建")

        return StepResult(True, {"storyboard": response})


class AuditHandler(StepHandler):
    """Run shenheyuan audit on current artifacts."""
    name = "审稿"
    description = "Audit content quality and accuracy"

    def execute(self) -> StepResult:
        # Collect all artifacts
        artifacts = {}
        for fname in ["选题研究报告.md", "知识点大纲.md", "配音稿_分段.txt",
                       "PPT大纲.md", "timeline.json", "image_slots.json"]:
            path = self.episode_dir / fname
            if path.exists():
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                artifacts[fname] = content[:1000]  # First 1000 chars

        audit_prompt = f"""你是一个严格的内容审核员（shenheyuan）。请审核以下视频制作物料，检查：
1. 信息准确性：有没有知识性错误？
2. 内容一致性：口播稿和PPT大纲是否对应同一件事？
3. 完整性：有没有遗漏关键知识点？
4. 格式合规：有无 ## ** 等不该出现的标记？

审核物料：
{json.dumps(artifacts, ensure_ascii=False, indent=2)[:3000]}

请输出审核报告。如果有问题，标注"❌ 问题：..."。如果全部通过，标注"✅ 全部通过"。
格式：纯文字"""
        
        try:
            response = _hermes_call("shenheyuan", audit_prompt, timeout=300)
            audit_path = self.episode_dir / "审核报告.md"
            with open(audit_path, "w", encoding="utf-8") as f:
                f.write(response)

            # Check if there are issues
            has_issues = "❌" in response
            print(f"  {'⚠️ 发现问题' if has_issues else '✅ 审核通过'}")
            print(f"  {'  请查看审核报告修正后重试' if has_issues else ''}")
            return StepResult(not has_issues, {"audit": response, "path": str(audit_path)})
        except Exception as e:
            return StepResult(True, {"audit": f"审核调用失败: {e}"})
