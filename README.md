# Make Learning Easy 🚀

> **AI视频全自动生产线 — 专注昇腾AI技术教程**
> 从选题到成片，全流程AI驱动，让知识传播变简单

---

## 📖 项目简介

**Make Learning Easy** 是一套面向 **昇腾AI技术栈** 的 AI 视频全自动生产线。

它融合了 **多Agent协作范式 + HyperFrames动画引擎 + 开源素材搜刮** 三大技术栈，实现了从选题研究 → 知识点整理 → 口播撰写 → TTS配音 → PPT设计 → 配图生成 → HyperFrames动画合成 → 视频渲染 → 字幕制作的**全流程自动化**。

### 核心能力

| 能力 | 说明 |
|------|------|
| 🧠 **多Agent协作** | 8个独立AI agent各司其职（选题研究员→知识点整理→编剧→美术指导→素材搜刮→创作者→剪辑师→字幕师） |
| 🎬 **HyperFrames引擎** | GSAP驱动的逐页动画合成，支持10+种布局变体，产出高质量技术教程视频 |
| 🎨 **75+设计系统** | 内置Liner、Mintlify、Vercel等75个品牌设计系统，每期可选3种风格 |
| 🔍 **开源素材搜刮** | 自动从Pexels等平台搜刮真实场景素材，提升视频真实感 |
| ✅ **三段式门禁** | 开工前→渲染前→交付前，每阶段自动校验质量，确保稳定复现 |

---

## 🏗️ 管线概览

```
T0 ──→ T1 ──→ T3 ──→ TTS ──→ T2 ──→ T4+T5 ──→ T6 ──→ T7 ──→ T8
选题   知识点   口播稿   实测    PPT大纲+   素材搜刮   HyperFrames  渲染+  字幕
研究   大纲     先行     时长    分镜设计    +AI配图   compositions  配音   (按需)
```

### 各阶段详解

| 阶段 | agent | 模型 | 产出 |
|------|-------|------|------|
| **T0** 选题研究 | `xuan-ti-yan-jiu-yuan` | deepseek-v4-pro | 选题范围定义、竞品分析 |
| **T1** 知识点大纲 | `yanjiuyuan` | deepseek-v4-pro | 结构化知识大纲 |
| **T3** 口播稿先行 🎤 | `bianju` | MiniMax-M2.7 | 口语化口播稿 |
| **TTS** 配音实测 | 启明 | edge-tts | 逐段配音+时长实测 |
| **T2** PPT大纲+分镜 | `meishu` | MiniMax-M2.7 | PPT大纲、timeline、配图规划 |
| **T4** 素材搜刮 | 启明(直管脚本) | — | 真实场景图片下载 |
| **T5** AI配图 | `chuangzuo` | ComfyUI/SDXL | AI生成配图素材 |
| **T6** Compositions 🎬 | `editor` | qwen3.6-plus | HyperFrames逐页动画 |
| **T7** 渲染+配音 | 启明 | hyperframes render | 最终视频输出 |
| **T8** 字幕(按需) | `zimu-agent` | — | ASS字幕封装 |

---

## 🚀 快速开始

### 环境要求

- **macOS** (M系列芯片)
- **Python 3.12+**
- **HyperFrames CLI** (`npm install -g @heygen/hyperframes`)
- **edge-tts** (`pip install edge-tts`)

### 启动新视频

```bash
# 一句话启动新项目
bash go.sh start '你的主题' 期号 [设计风格]

# 示例
bash go.sh start '昇腾NPU架构解析' 4 mintlify

# 逐步推进
bash go.sh step 第4期_昇腾NPU架构解析
```

### 管线控制

```bash
bash go.sh status 第4期_项目名    # 查看状态
bash go.sh repair 第4期_项目名    # 修复异常步骤
bash go.sh check  第4期_项目名    # 门禁检查
bash go.sh list                  # 列出所有项目
```

---

## 📁 项目结构

```
make-learning-easy/
├── AGENTS.md              ← 单一真相源（全部管线规范）
├── PIPELINE.md            ← 快速参考
├── PIPELINE_PLAN.md       ← 完整融合管线规划文档
├── BLOCKS.md              ← HyperFrames Block 目录
├── go.sh                  ← 统一入口脚本
├── scripts/
│   ├── pipeline.py        ← 状态编排器
│   ├── harness.py         ← 三段式门禁
│   ├── generate_composition.py  ← 10种布局模板
│   ├── images_to_base64.py      ← 图片转base64
│   └── ...
├── designs/
│   └── awesome-design-md/ ← 75种品牌设计系统
├── episodes/
│   ├── 第1期_连上服务器/         ← 已完成
│   ├── 第2期_昇腾部署Qwen3-VL-8B/
│   └── ...
└── specs/
    └── AGENTS.md           ← 管线规范副本
```

---

## 🎯 当前系列：昇腾模型部署及调优

| 期数 | 主题 | 状态 |
|------|------|------|
| 第1期 | 连上服务器 | ✅ 已完成 |
| 第2期 | 昇腾部署Qwen3-VL-8B概念讲解 | 🔄 制作中 |
| 第3期 | Qwen3.5-9B推理调优 | 📋 已规划 |
| 后续 | 更多... | 📋 待定 |

---

## 🛠️ 设计风格

内置 **75个品牌设计系统**（来自 awesome-design-md），每期视频可选3种风格让主人挑选：

- **Mintlify** — 白底绿强调，简洁清新
- **Linear** — 深色主题，科技感强
- **Vercel** — 黑白极简，专业大气
- **Snappify** — 代码展示优化，开发者友好
- 以及更多...

---

## 📜 核心原则

1. **口播先行** — 先写口播稿→TTS实测时长→再做PPT，确保声画对齐
2. **图片base64内联** — 所有图片内嵌到HTML中，不依赖文件系统
3. **每页不同布局** — 10种布局轮换，相邻页不重复
4. **三段式门禁** — 开工前/渲染前/交付前自动校验
5. **多Agent独立思考** — 不跳过任何agent，每步都有独立审核

---

## 👨‍💻 关于

**维护者**: [Shi-zhangbin](https://github.com/Shi-zhangbin)  
**技术栈**: Python · HyperFrames · GSAP · edge-tts · ComfyUI · SDXL  
**定位**: 一人公司 · B站技术教程 · 昇腾AI布道

---

> ✨ **Make Learning Easy** — 让学习变简单，让知识无障碍传播
