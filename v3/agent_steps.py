"""
v3/agent_steps.py — 内容生成步骤（Codex 直接生成）

每个 handler 只做：验证前置条件 → 打印生成提示 → Codex 按 SKILL.md 生成内容。
不做模板填充，不做内容生成。
"""
import json, os, re
from pathlib import Path
from v3.config import FILE_NAMES
from v3.steps.base import StepHandler, StepResult


def _get_feedback(episode_dir: str) -> str:
    fp = Path(episode_dir) / "gate-feedback.json"
    if not fp.exists():
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
        print(f"\n  📝 需要生成选题报告")
        print(f"     主题: {topic}")
        print(f"     输出: {FILE_NAMES["topic_report"]}")
        print(f"     参考 SKILL.md T0 章节")
        if feedback:
            print(f"     反馈: {feedback}")
        
        # 写入 prompt 文件供 Codex 读取
        prompt = {
            "step": "T0", "topic": topic, "feedback": feedback,
            "output": FILE_NAMES["topic_report"],
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",

        }
        (self.episode_dir / "step-prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {
            "prompt": str(self.episode_dir / "step-prompt.json"),
            "topic": topic
        })


class OutlineHandler(StepHandler):
    """T1: 知识点大纲"""
    name = "T1"
    description = "Generate knowledge outline"

    def execute(self) -> StepResult:
        report_path = self.episode_dir / FILE_NAMES["topic_report"]
        report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        feedback = _get_feedback(str(self.episode_dir))
        
        print(f"\n  📝 需要生成知识点大纲")
        print(f"     来源: {FILE_NAMES["topic_report"]}")
        print(f"     输出: {FILE_NAMES["outline"]}")
        print(f"     参考 SKILL.md T1 章节")
        if feedback:
            print(f"     反馈: {feedback}")
        
        prompt = {
            "step": "T1", "report": report[:500], "feedback": feedback,
            "output": FILE_NAMES["outline"],
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",

        }
        (self.episode_dir / "step-prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {"prompt": str(self.episode_dir / "step-prompt.json")})


class ScriptHandler(StepHandler):
    """T2: 口播稿"""
    name = "T2"
    description = "Generate narration script"

    def execute(self) -> StepResult:
        outline_path = self.episode_dir / FILE_NAMES["outline"]
        outline = outline_path.read_text(encoding="utf-8") if outline_path.exists() else ""
        feedback = _get_feedback(str(self.episode_dir))
        
        print(f"\n  📝 需要生成口播稿")
        print(f"     来源: {FILE_NAMES["outline"]}")
        print(f"     输出: {FILE_NAMES["script"]}")
        print(f"     参考 SKILL.md T2 章节")
        print(f"     风格: B站科技UP主 — 跟朋友聊天的感觉，用梗讲干货")
        if feedback:
            print(f"     反馈: {feedback}")
        
        prompt = {
            "step": "T2", "outline": outline[:1000], "feedback": feedback,
            "output": FILE_NAMES["script"],
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",
            "tone_style": "bilibili_up主",
            "script_style_guide": (
                "以B站科技UP主的口吻输出口播稿。具体要求：\n1. 开头用一个日常生活场景或互联网热点破题，让观众有代入感（比如刷到个新闻、刷视频时的发现、买了个新设备），不用程序员办公室段子\n2. 语气像跟朋友聊天，多用'家人们'、'懂的都懂'、'咱就是说'、'你细品'等UP主常用口癖\n3. 每个知识点之间用网络热梗或B站名场面过渡，保持年轻化表达节奏\n4. 把技术概念类比成大家熟悉的日常场景，少用程序员专属类比\n5. 适当加入'三连'、'投币'、'弹幕护体'等B站文化元素，让观众有参与感\n6. 干货内核必须保留，不能为了玩梗牺牲准确性\n7. 每段结尾可以加一句互动式结尾，模拟和观众对话\n8. 排版上像随口在聊，不用追求每句都押韵或节奏工整，要的是'听着不累'"
            ),
            "validation_rules": {
                "must_not_contain": [
                    "章节标题（一、二、三...）",
                    "舞台指示（（开场）（停顿）（完））",
                    "分隔线（=== ---）",
                    "元数据行（音频配音稿、目标时长等）",
                    "Markdown 标记（## ** ``）",
                    "占位符（TKTK TODO 此处插入）"
                ],
                "must_contain": [
                    "分页标记（--- P1, --- P2, ...）",
                ],
                "minimum_pages": 5,
                "tone": "B站科技UP主，口语化，像跟朋友聊天，纯口播文字"
            },
            "page_plan_required": True,
            "page_plan_filename": "02-page-plans.json",
            "page_plan_instructions": "除了 02-script.txt，你还需要输出 02-page-plans.json。这个文件为每一页定义视觉结构，T6 直接用它来渲染页面。\n每页包含以下字段：\n  - page: 页码（与 --- P{N} 对应）\n  - layout: 布局类型，可选 hero / concept / flipped / comparison / code_block / flowchart / card_grid / quote / section_divider / outro\n  - heading: 这一页的大标题，用口语化的短语（10字以内）\n  - subtitle: 副标题或一句话概述（选填，null 也可以）\n  - emoji: 一个 emoji 代表这页主题\n  - accent_line: 布尔值，是否在标题下方显示强调线（hero/section_divider 建议 true）\n  - tags: 标签列表（仅 hero 页用）\n  - cards: 卡片列表，每张卡片有 icon / title / body\n    card 数量由本页内容密度决定，3个要点就用3张\n    title 是语义化的简短标题（不超过10字），不是截断句\n    body 是此要点的完整解释（1-2句话）\n  - code: 代码对象（仅 code_block 页用），有 language 和 body 字段\n  - comparison: 对比对象（仅 comparison 页用），有 left_title / left_items / right_title / right_items\n  - flow_steps: 步骤列表（仅 flowchart 页用），每步有 icon / title / body\n  - quote: 引语（仅 quote 页用），可以代替 heading/subtitle\n  - image: 图片意图对象，含字段：\n      required: true/false，这页是否需要配图\n      position: left / right / bottom / background\n      concept: 画面概念描述（20字左右），告诉 T4 这页需要传达什么画面信息\n      style_hint: 风格建议（选填）\n    image 的 prompt 由 T4 负责写，此处只传递意图\n规则：\n  1. 每个 page 只能设一种内容结构字段：cards / code / comparison / flow_steps / quote 四选一\n  2. layout 和 image.position 共同决定最终的排版方式\n  3. 卡片数 = 本页的核心要点数，不要为了凑数硬塞\n  4. 不需要写图片的完整 prompt，那是 T4 的任务\n  5. 不要在这份 JSON 里出现占位符",

        }
        (self.episode_dir / "step-prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {"prompt": str(self.episode_dir / "step-prompt.json")})


class StoryboardHandler(StepHandler):
    """T4: 分镜设计"""
    name = "T4"
    description = "Design storyboard and image slots"

    def execute(self) -> StepResult:
        script_path = self.episode_dir / FILE_NAMES["script"]
        script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
        feedback = _get_feedback(str(self.episode_dir))
        
        print(f"\n  📝 需要生成分镜方案")
        print(f"     来源: {FILE_NAMES["script"]}")
        print(f"     输出: {FILE_NAMES["storyboard"]} + {FILE_NAMES["image_slots"]}")
        print(f"     参考 SKILL.md T4 章节")
        print(f"     风格: 二次元动漫视觉 — 每页像一帧B站动画截图")
        if feedback:
            print(f"     反馈: {feedback}")
        
        prompt = {
            "step": "T4", "script": script[:1000], "feedback": feedback,
            "output": FILE_NAMES["storyboard"] + " + " + FILE_NAMES["image_slots"],
            "design_style": self.design.get("name", "bilibili"),
            "forbidden_patterns": ["卡片", "图片", "图表", "TKTK", "TODO", "占位", "placeholder", "此处插入", "这里放", "请插入", "示例文本"],
            "min_duration_hint": "目标10分钟以上（约3000-4000字），不要压缩内容",
            "tone_style": "bilibili_up主",
            "visual_style_guide": (
                "设计分镜和配图描述时，采用日系二次元动漫风格。具体要求：\n1. image_slots 中的 prompt 描述必须指向 anime / 动漫绘画风格，禁止写实照片\n2. 参考新海诚/京都动画等视觉语言：柔和的线条、鲜艳但有层次的色彩、光影通透\n3. 人物（如有）使用二次元画风：大眼睛表情丰富、头发有光泽、肤色柔和\n4. 技术概念和抽象内容用动漫化方式表达（比如：数据流变成发光的魔法阵、Bug变成卖萌的小怪兽）\n5. 每页像一帧动画截图，有明确的视觉焦点和氛围感\n6. 背景用渐变天空/云彩/光晕等 anime 经典元素增强沉浸感\n7. 色调与 bilibili 风格色板协调（主色粉 #FB7299、辅助蓝 #00A1D6）\n8. 避免恐怖、血腥、恐怖谷等不适内容\n9. 参考 B站动画区常见视觉风格，让观众第一眼就知道这是二次元向内容"
            ),
            "validation_rules": {
                "image_slots_required_fields": ["filename", "prompt", "page", "slot_index"],
                "minimum_slots": 5,
                "must_not_contain": [
                    "占位符（TKTK TODO 图片 此处插入）"
                ],
                "image_style": "日系二次元动漫风格配图描述，anime绘画风格"
            },
            "image_intent_available_from": "02-page-plans.json",
            "image_intent_instructions": (
                "如果 02-page-plans.json 存在，你必须在生成 image_slots 之前先读取它。"
                "page-plans 中每页的 image 字段提供了画面意图：\n"
                "  - required: 这页是否需要配图（false 则该页不需要写 slot）\n"
                "  - position: 图片在页面上的位置\n"
                "  - concept: 画面概念（T2 的设计意图）\n"
                "  - style_hint: 风格建议\n\n"
                "你的任务：把 concept 扩充为具体、可执行的 prompt。不允许直接复制 concept 当 prompt。\n"
                "一个好的 prompt 应该包含：主体、动作、环境、风格、色调。\n"
                "例：\n"
                "  概念: → 程序A通过API网关向程序B发请求，中间人分隔两边\n"
                "  写出的 prompt: → 一个程序员坐在电脑前，屏幕上两个程序模块中间有一个标记着API的网关，\n"
                "  通过云朵状箭头连接，漫画风格，简洁背景，暖色调"
            ),

        }
        (self.episode_dir / "step-prompt.json").write_text(
            json.dumps(prompt, ensure_ascii=False, indent=2))
        
        return StepResult(True, {"prompt": str(self.episode_dir / "step-prompt.json")})


class AuditHandler(StepHandler):
    """内容审核"""
    name = "审稿"
    description = "Review content quality"

    def execute(self) -> StepResult:
        artifacts = {}
        for fname in [FILE_NAMES["topic_report"], FILE_NAMES["outline"], FILE_NAMES["script"], FILE_NAMES["storyboard"]]:
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
