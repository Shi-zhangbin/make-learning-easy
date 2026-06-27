# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Make Learning Easy** — AI 视频全自动生产线。输入一个主题，走完 T0→T7 管线，产出成品 MP4 视频。专注于技术教程和知识科普内容。

## Essential Commands

```bash
# 一键全自动创建期目
bash go.sh create "2026-06-27_什么是API_[Codex]" --topic "..." --auto

# 分步运行
bash go.sh run --episode "2026-06-27_什么是API_[Codex]" --step T5

# 查看状态
bash go.sh status --episode "2026-06-27_什么是API_[Codex]"
bash go.sh list
bash go.sh designs

# 分步创建（参数：name, --topic）
python3 -m v3.engine init "2026-06-27_什么是API_[Codex]" --topic "..." --style bilibili

# 依赖安装
pip install -r requirements.txt
npm install   # HyperFrames 渲染引擎
```

## Pipeline

```
T0(选题) → T1(大纲) → T2(口播稿) → T3(配音+字幕) → T4(分镜) → T5(配图) → T6(Composition) → T7(渲染)
```

- **自动步骤**: T3 (edge-tts 配音), T5 (三级兜底配图), T6 (元素驱动合成), T7 (HyperFrames 渲染)
- **Agent 步骤**: T0/T1/T2/T4 — engine 输出 `.step_prompt.json` → Agent 生成内容 → 删除 `.step_prompt.json` → 重新执行 → 门禁通过后推进
- T2(TTS) 在 T4 之前: 先有真实音频时长，再做分镜
- 每步后自动跑门禁检查（gate_master.py）: 占位符检测、时长校验、配图质量、黑帧检测

## Architecture

### 核心文件

| 文件 | 职责 |
|------|------|
| `v3/engine.py` | 管线编排引擎 — init/run/status/create 命令调度 + 状态机 |
| `v3/config.py` | API keys + 环境配置（wuyinkeji/Pexels/Pixabay key、视频尺寸、TTS 参数） |
| `v3/agent_steps.py` | Agent 步骤的提示词（TopicResearch/Outline/Script/StoryboardHandler） |
| `v3/imagegen.py` | 三级兜底配图: wuyinkeji(AI) → pexels(照片) → pixabay(照片) → SVG |
| `v3/gates/gate_master.py` | 门禁检查器 — 每步产出的质量门禁（内容、时长、配图、风格、黑帧） |
| `v3/steps/tts.py` | edge-tts 配音 + 字幕生成 |
| `v3/steps/t5_images.py` | T5 配图生成 handler |
| `v3/steps/t6_compositions.py` | 元素驱动 HyperFrames composition 引擎 |
| `v3/steps/t7_render.py` | HyperFrames 渲染 + ffmpeg 音视频合成 |
| `v3/designs/` | 设计预设系统 — YAML 定义颜色/字体/间距，预设见 `presets/*.yaml` |
| `v3/subtitle.py` | 字幕处理（SRT/ASS） |
| `go.sh` | 主入口 — 包装 `python3 -m v3.engine` |
| `AGENTS.md` | Agent 与开发者协作准则 |

### 项目结构

```
make-learning-easy/
├── go.sh                    # 主入口
├── AGENTS.md                # Agent 协作准则（每次任务前必读）
├── CLAUDE.md                ← 本文件
├── v3/                      # 管线引擎核心
│   ├── engine.py            # 编排 + 状态机
│   ├── steps/               # 各步骤实现
│   ├── gates/               # 门禁检查
│   ├── designs/presets/     # 设计预设（7+1 套 YAML）
│   └── assets/              # GSAP 动画库
├── scripts/                 # 辅助脚本（较早的管线版本/工具）
│   ├── pipeline.py          # ascend-pipeline 旧版编排器
│   ├── generate_images.py   # 配图生成
│   ├── composition_helper.py
│   ├── tts_to_durations.py
│   └── harness.py           # 合成校验
├── episodes/                # 每期视频的内容目录
│   └── 第N期_主题/
│       ├── pipeline_state.json  # 管线状态
│       ├── timeline.json        # 元素数组 + 时长
│       ├── audio/               # TTS 音频 + 字幕
│       ├── images/              # 配图
│       ├── compositions/        # HTML 场景
│       └── 成品/                # final.mp4
└── skills/                  # Codex agent 技能
```

### 设计预设

8 套预设，通过 `python3 -m v3.engine init "..." --style <name>` 指定：

| 预设 | 底色 | 强调色 | 风格 |
|------|------|--------|------|
| bilibili（默认） | 浅灰 `#F5F6F7` | 粉 `#FB7299` | B站二次元科技 |
| talk-show（分支） | 浅灰 `#F0F2F5` | 暖橙 `#FF6B35` | 程序员脱口秀 |
| claude | 暖白 `#faf9f5` | 珊瑚 `#cc785c` | 暖色人文 |
| dark-teal | 深灰 `#0A0C0E` | 青绿 `#4FC3A1` | 深色科技 |
| linear/mintlify/stripe/vercel | 详见 YAML | — | 各品牌风格 |

### API Keys

- `.env` 中配置，gitignored（参考 `.env.example`）
- **WUYINKEJI_KEY**: 主力 AI 生图（image2 模型），兜底链 wuyinkeji → pexels → pixabay → SVG
- **PEXELS_API_KEY / PIXABAY_API_KEY**: 真实照片搜索兜底
- 不使用 OPENAI_API_KEY，相关代码已移除

## Core Rules (from AGENTS.md)

1. **默认 bilibili 风格**: 创建期目时一律 `--style bilibili`，除非用户明确指定其他
2. **视频时长校验**: T2 口播稿后估算 `字符数 / 4.2` 秒数 < 目标分钟×60×0.85 则退回加内容
3. **禁止占位符**: 内容文件不得含"卡片、图片、图表、TKTK、TODO、此处插入"等
4. **只处理用户指定的期目**: 不扫描 `episodes/` 做推测性工作
5. **所有产出必须在期目目录内**: 不向 `episodes/` 根目录、仓库根目录写文件

## Branches

- **main**: 核心管线，通用风格
- **codex/bilibili-video-making**: 完整 B站风格改造（弹幕浮层、吐槽气泡、talk-show 预设、二次元分镜提示词）
- **codex/bottom-progress-bar**: 底部进度条改造（当前工作分支）

### 分支工作规范

不要自动同步远程仓库。切换分支时只用 `git checkout`，不附带 `git pull` / `git fetch`，除非用户明确要求。用户在本地开发期间，所有操作限制在本地，推送由用户自己决定。

## Known Risks

| 风险 | 说明 |
|------|------|
| T7 渲染慢 | GSAP + HyperFrames 长视频并行帧采集可能超时，降级到单 worker |
| 中文路径字幕 | ffmpeg subtitles filter 在 Homebrew 默认不含 libass |
| 配图质量 | JPEG 压缩默认 -q:v 3，图片约 50-80KB |
| HyperFrames 闭源 | 渲染引擎 proprietary npm 包，核心逻辑不可修改 |
