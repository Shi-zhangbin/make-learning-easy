"""
v3/agent_steps.py — 内容生成步骤（Codex 直接生成）

每个 handler 只做：验证前置条件 → 打印生成提示 → Codex 按 SKILL.md 生成内容。
不做模板填充，不做内容生成。
"""
import json, os, re
from pathlib import Path
from v3.steps.base import StepHandler, StepResult


def _get_feedback(episode_dir: str) -> str:
    fp = Path(episode_dir) / ".gate_feedback.json"
    if fp.exists():
        try:
            with open(fp, encoding="utf-8") as f:
                fb = json.load(f)
            issues = fb.get("issues", [])
            if issues:
                return "\n[门禁反馈 - 需要修复以下问题]:\n" + "\n".join(f"- {i}" for i in issues)
        except:
            pass
    return ""


class TopicResearchHandler(StepHandler):
    """T0: 选题报告"""
    name = "T0"
    description = "Generate topic research report"

    def __init__(self, episode_dir: str, design: dict = None, topic: str = ""):
        super().__init__(episode_dir, design)
        self.topic = topic

    def execute(self) -> StepResult:
        topic = self.topic or "未指定主题"
        feedback = _get_feedback(str(self.episode_dir))
        
        # 打印提示供 Codex 使用
        print(f"\n  📝 需要生成选题研究报告")
        print(f"     主题: {topic}")
        print(f"     输出: 选题研究报告.md")
        print(f"     参考 SKILL.md T0 章节")
        if feedback:
            print(f"     反馈: {feedback}")
        
        # 写入 prompt 文件供 Codex 读取
        prompt = {
            "step": "T0", "topic": topic, "feedback": feedback,
            "output": "选题研究报告.md",
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",

        }
        (self.episode_dir / ".step_prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {
            "prompt": str(self.episode_dir / ".step_prompt.json"),
            "topic": topic
        })


class OutlineHandler(StepHandler):
    """T1: 知识点大纲"""
    name = "T1"
    description = "Generate knowledge outline"

    def execute(self) -> StepResult:
        report_path = self.episode_dir / "选题研究报告.md"
        report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        feedback = _get_feedback(str(self.episode_dir))
        
        print(f"\n  📝 需要生成知识点大纲")
        print(f"     来源: 选题研究报告.md")
        print(f"     输出: 知识点大纲.md")
        print(f"     参考 SKILL.md T1 章节")
        if feedback:
            print(f"     反馈: {feedback}")
        
        prompt = {
            "step": "T1", "report": report[:500], "feedback": feedback,
            "output": "知识点大纲.md",
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",

        }
        (self.episode_dir / ".step_prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {"prompt": str(self.episode_dir / ".step_prompt.json")})


class ScriptHandler(StepHandler):
    """T2: 口播稿"""
    name = "T2"
    description = "Generate narration script"

    def execute(self) -> StepResult:
        outline_path = self.episode_dir / "知识点大纲.md"
        outline = outline_path.read_text(encoding="utf-8") if outline_path.exists() else ""
        feedback = _get_feedback(str(self.episode_dir))
        
        print(f"\n  📝 需要生成口播稿")
        print(f"     来源: 知识点大纲.md")
        print(f"     输出: 配音稿_分段.txt")
        print(f"     参考 SKILL.md T2 章节")
        print(f"     风格: 程序员脱口秀 — 用段子讲干货，自嘲式叙述")
        if feedback:
            print(f"     反馈: {feedback}")
        
        prompt = {
            "step": "T2", "outline": outline[:1000], "feedback": feedback,
            "output": "配音稿_分段.txt",
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",
            "tone_style": "standup_comedy",
            "script_style_guide": (
                "以程序员脱口秀的形式输出口播稿。具体要求：\n1. 开头用一个程序员日常翻车场景破题，比如修bug、上线事故、跟产品经理battle\n2. 每个知识点由一个程序员梗或自嘲引出，不要干巴巴直接讲概念\n3. 把技术概念类比成程序员日常（比如：Git分支就像你周五下午改完代码没commit就下班）\n4. 使用'咱就是说'、'你懂的'这种程序员社交语气\n5. 每段正文后可以跟一句吐槽或反省\n6. 干货内核必须保留，不能为了搞笑牺牲准确性\n7. 标题风格参考'给傻子的X教程'、'从入门到跑路'\n8. 用人类听得懂的方式讲技术故事"
            ),

        }
        (self.episode_dir / ".step_prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {"prompt": str(self.episode_dir / ".step_prompt.json")})


class StoryboardHandler(StepHandler):
    """T4: 分镜设计"""
    name = "T4"
    description = "Design storyboard and image slots"

    def execute(self) -> StepResult:
        script_path = self.episode_dir / "配音稿_分段.txt"
        script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
        feedback = _get_feedback(str(self.episode_dir))
        
        print(f"\n  📝 需要生成分镜方案")
        print(f"     来源: 配音稿_分段.txt")
        print(f"     输出: PPT大纲.md + image_slots.json")
        print(f"     参考 SKILL.md T4 章节")
        print(f"     风格: 漫画/二次元视觉 — 每页像一帧梗图")
        if feedback:
            print(f"     反馈: {feedback}")
        
        prompt = {
            "step": "T4", "script": script[:1000], "feedback": feedback,
            "output": "PPT大纲.md + image_slots.json",
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",
            "tone_style": "standup_comedy",
            "visual_style_guide": (
                "设计分镜和配图描述时，采用漫画/二次元风格。具体要求：\n1. image_slots 中的 prompt 描述应指向插画/漫画风格，不要写实照片\n2. 每页视觉参考'梗图'的感觉：大字+夸张表情+简洁背景\n3. 程序员场景用抽象化、夸张化的视觉表达（比如：bug变成小怪兽）\n4. 代码截图页面保持清晰，但周围可以加吐槽标注\n5. 避免恐怖、血腥、恐怖谷等不适内容\n6. 每一页的视觉焦点要明确，配合脱口秀节奏"
            ),

        }
        (self.episode_dir / ".step_prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {"prompt": str(self.episode_dir / ".step_prompt.json")})


class AuditHandler(StepHandler):
    """内容审核"""
    name = "审稿"
    description = "Review content quality"

    def execute(self) -> StepResult:
        artifacts = {}
        for fname in ["选题研究报告.md", "知识点大纲.md", "配音稿_分段.txt", "PPT大纲.md"]:
            path = self.episode_dir / fname
            if path.exists():
                artifacts[fname] = path.read_text(encoding="utf-8")[:300]
        
        has_issues = False
        report = ["# 内容审核报告\n"]
        for fname, content in artifacts.items():
            for pat, name in [(r'#{2,}', "##"), (r'\*{2,}', "**"), (r'`+', "``")]:
                if re.search(pat, content):
                    report.append(f"- ❌ {fname}: 含残留标记 {name}")
                    has_issues = True
        if not has_issues:
            report.append("✅ 全部通过")
        
        (self.episode_dir / "审核报告.md").write_text("\n".join(report), encoding="utf-8")
        return StepResult(not has_issues, {"report": "\n".join(report), "has_issues": has_issues})
