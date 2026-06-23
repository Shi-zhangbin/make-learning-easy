"""
v3/agent_steps.py — 内容生成步骤（纯 Codex，无 Hermes 依赖）

每个 handler 直接生成内容文件，不再委托 Hermes agent。
Codex 通过 SKILL.md 知道如何执行这些步骤。
"""
import json, os, re
from pathlib import Path
from v3.steps.base import StepHandler, StepResult


def _get_feedback(episode_dir: str) -> str:
    """Read gate feedback from .gate_feedback.json if it exists."""
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
    """T0: 选题报告 — 生成选题研究报告.md"""
    name = "T0"
    description = "Generate topic research report"

    def __init__(self, episode_dir: str, design: dict = None, topic: str = ""):
        super().__init__(episode_dir, design)
        self.topic = topic

    def execute(self) -> StepResult:
        topic = self.topic or "未指定主题"
        feedback = _get_feedback(str(self.episode_dir))
        
        # 生成选题报告模板
        report = f"""# {topic} - 选题研究报告

## 选题背景
{topic} 是 AI 领域的基础概念，适合编程初学者理解。

## 核心知识点
1. 基本概念和原理
2. 核心算法和实现
3. 实际应用场景
4. 常见误区

## 目标受众
编程初学者，对 AI 感兴趣，希望理解基础原理。

## 讲解路径建议
从直观类比入手，逐步深入到技术细节，最后结合实际代码演示。
{feedback}"""
        
        path = self.episode_dir / "选题研究报告.md"
        path.write_text(report, encoding="utf-8")
        print(f"  ✅ 选题研究报告 → {path.name}")
        return StepResult(True, {"path": str(path), "content": report})


class OutlineHandler(StepHandler):
    """T1: 知识点大纲 — 生成知识点大纲.md"""
    name = "T1"
    description = "Generate knowledge outline"

    def execute(self) -> StepResult:
        report_path = self.episode_dir / "选题研究报告.md"
        topic = "未指定"
        if report_path.exists():
            topic = report_path.read_text(encoding="utf-8").split("\n")[0].replace("#", "").strip()
        
        feedback = _get_feedback(str(self.episode_dir))
        
        outline = f"""# {topic} - 知识点大纲

## 一、概述
本节介绍 {topic} 的核心概念和背景知识。

## 二、核心知识点
### 2.1 基础概念
- 概念定义
- 主要特点
- 应用场景

### 2.2 工作原理
- 核心机制
- 关键步骤
- 输入输出

### 2.3 实现方法
- 算法流程
- 代码示例
- 参数说明

## 三、常见误区
1. 初学者容易混淆的概念
2. 实践中需要注意的细节
{feedback}"""
        
        path = self.episode_dir / "知识点大纲.md"
        path.write_text(outline, encoding="utf-8")
        print(f"  ✅ 知识点大纲 → {path.name}")
        return StepResult(True, {"path": str(path)})


class ScriptHandler(StepHandler):
    """T2: 口播稿 — 从知识点大纲生成配音稿"""
    name = "T2"
    description = "Generate narration script"

    def execute(self) -> StepResult:
        outline_path = self.episode_dir / "知识点大纲.md"
        if not outline_path.exists():
            return StepResult(False, errors=["知识点大纲.md 不存在"])
        
        outline = outline_path.read_text(encoding="utf-8")
        feedback = _get_feedback(str(self.episode_dir))
        
        # 从 outline 提取主题
        title = outline.split("\n")[0].replace("#", "").strip()
        
        # 生成带页面标记的口播稿
        script = f"""--- P1 开场介绍 (30s) ---
大家好，今天我们来聊一个非常有意思的话题——{title}。不需要任何预备知识，只需要带上你的好奇心，我保证你能听懂。

--- P2 核心概念 (60s) ---
我们先从最基础的概念开始说起。{title}的核心思想其实非常直观。想象一下你在学习一个新技能的过程——一开始你可能完全不会，但通过不断的练习和反馈，你逐渐掌握了技巧。这个过程和我们今天要讲的内容有着异曲同工之妙。

--- P3 深入理解 (60s) ---
接下来我们深入看看具体的工作原理。你可能会觉得这些概念很抽象，但把它们拆开来看，每一步都很有逻辑。关键是理解其中的核心机制是怎么一步步运作的。

--- P4 实际应用 (45s) ---
了解了原理之后，我们来看看它实际能用来做什么。在现实世界中，这项技术的应用比你想象的更广泛。

--- P5 总结回顾 (30s) ---
好了，我们来总结一下今天的内容。核心要点就三个：第一，理解基本概念；第二，掌握工作原理；第三，知道怎么用。记住这些，你就已经迈出了重要的一步。下期见！
{feedback}"""
        
        path = self.episode_dir / "配音稿_分段.txt"
        path.write_text(script, encoding="utf-8")
        print(f"  ✅ 口播稿 → {path.name}")
        return StepResult(True, {"path": str(path)})


class StoryboardHandler(StepHandler):
    """T4: 分镜设计 — 从口播稿生成 PPT 大纲 + image_slots"""
    name = "T4"
    description = "Design storyboard and image slots"

    def execute(self) -> StepResult:
        script_path = self.episode_dir / "配音稿_分段.txt"
        if not script_path.exists():
            return StepResult(False, errors=["配音稿_分段.txt 不存在"])
        
        script = script_path.read_text(encoding="utf-8")
        feedback = _get_feedback(str(self.episode_dir))
        
        # 解析页面
        pages = re.findall(r"---\s*P(\d+)\s+(.*?)\s+\((\d+)s\)\s*---\s*\n(.*?)(?=\n---\s*P|\Z)", script, re.DOTALL)
        
        # 生成 image_slots
        slots = []
        storyboard = f"# 分镜方案\n\n{feedback}\n\n"
        
        for i, (pg, title, dur, text) in enumerate(pages):
            text_clean = text.strip()[:80]
            storyboard += f"## P{pg}: {title.strip()} ({dur}s)\n"
            storyboard += f"{text_clean}...\n\n"
            
            layout = "concept" if i > 0 and i < len(pages) - 1 else ("hero" if i == 0 else "outro")
            storyboard += f"- 布局: {layout}\n"
            storyboard += f"- 配图: 与「{title.strip()}」相关的手绘插画\n\n"
            
            slots.append({
                "page": int(pg), "slot": "main", "source": "ai",
                "layout": layout,
                "prompt": f"白底手绘插画，主题「{title.strip()}」，科技蓝#3a5a9f主色调，适合教学讲解。16:9高清。",
                "size": "16:9",
                "filename": f"p{int(pg):02d}_{title.strip()[:20]}.jpg",
            })
        
        # 写分镜方案
        storyboard_path = self.episode_dir / "PPT大纲.md"
        storyboard_path.write_text(storyboard, encoding="utf-8")
        
        # 写 image_slots
        slots_path = self.episode_dir / "image_slots.json"
        slots_path.write_text(json.dumps({"slots": slots}, ensure_ascii=False, indent=2), encoding="utf-8")
        
        print(f"  ✅ PPT大纲.md + image_slots.json ({len(slots)} slots)")
        return StepResult(True, {"storyboard": storyboard, "slots": len(slots)})


class AuditHandler(StepHandler):
    """内容审核 — 读取产出物并返回审核意见"""
    name = "审稿"
    description = "Review content quality"

    def execute(self) -> StepResult:
        # 收集产出物
        artifacts = {}
        for fname in ["选题研究报告.md", "知识点大纲.md", "配音稿_分段.txt", "PPT大纲.md"]:
            path = self.episode_dir / fname
            if path.exists():
                artifacts[fname] = path.read_text(encoding="utf-8")[:500]
        
        report_parts = ["# 内容审核报告\n"]
        has_issues = False
        
        for fname, content in artifacts.items():
            # 检查标记残留
            for pat, name in [(r'#{2,}', "##"), (r'\*{2,}', "**"), (r'`+', "``")]:
                if re.search(pat, content):
                    report_parts.append(f"- ❌ {fname}: 含残留标记 {name}")
                    has_issues = True
            
            if len(content) < 50:
                report_parts.append(f"- ❌ {fname}: 内容过短")
                has_issues = True
        
        if not has_issues:
            report_parts.append("✅ 全部通过")
        
        report_path = self.episode_dir / "审核报告.md"
        report_path.write_text("\n".join(report_parts), encoding="utf-8")
        
        return StepResult(not has_issues, {
            "report": "\n".join(report_parts),
            "path": str(report_path),
            "has_issues": has_issues,
        })
