# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Make Learning Easy** — AI 视频全自动生产线。输入一个主题，走完 T0→T7 管线，产出成品 MP4 视频。专注于技术教程和知识科普内容。

## Essential Commands

```bash
# 一键全自动创建期目
bash go.sh create "2026-06-27_什么是API_-Claude-Code" --topic "..." --auto

# 分步运行
bash go.sh run --episode "2026-06-27_什么是API_-Claude-Code" --step T5

# 查看状态
bash go.sh status --episode "2026-06-27_什么是API_-Claude-Code"
bash go.sh list
bash go.sh designs

# 分步创建（参数：name, --topic）
python3 -m v3.engine init "2026-06-27_什么是API_-Claude-Code" --topic "..." --style bilibili

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
4. **配音稿纯口播**: `02-script.txt` 只含口播文字，无元数据/舞台指示/章节标题/分隔线
5. **只处理用户指定的期目**: 不扫描 `episodes/` 做推测性工作
6. **所有产出必须在期目目录内**: 不向 `episodes/` 根目录、仓库根目录写文件

## Pipeline 反馈机制

### Gate 反馈闭环

Gate 失败时引擎会写 `gate-feedback.json` 到期目目录，里面包含 `issues`（问题列表）和 `feedback_target`（退回步骤）。重新运行同一步骤时，Agent 应先读取此文件，修复内容后重试。Gate 通过后文件自动删除。

### Pre-Condition 快速失败

部分步骤在 `execute()` 前会跑 `pre_condition()` 前置检查，拦截常见错误：

| 步骤 | Pre-condition 检查 |
|------|-------------------|
| T3 | 脚本必须有 ≥2 个 `--- Px` 分页标记 |
| T5 | `image_slots.json` 每个 slot 必须有 `filename/prompt/page/slot_index` |
| T6 | `timeline.json` 必须有 ≥5 个 slide |
| T7 | Composition HTML 必须存在（缺 `index.html` 则自动补） |

### Step-prompt 校验规则

T2/T4 的 `step-prompt.json` 含 `validation_rules` 字段，明确告诉 Agent 内容必须满足什么条件、禁止出现什么模式。Agent 写内容前应先读这个字段自检。

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
| T2 脚本格式 | T2 gate 新增检测舞台指示/章节标题/分隔线/分页标记，防止 TTS 念废词 |
| T4 image_slots | 新增每个 slot 必填字段校验（filename/prompt/page/slot_index），T5 pre_condition 拦截 |
| 目录名 `[` `]` | 命名已改为 `-Agent` 格式，不再使用方括号，避免 `glob.glob()` 语法错误 |
| HyperFrames 闭源 | 渲染引擎 proprietary npm 包，核心逻辑不可修改 |
| 口播稿开头不在 P1 内 | 开场白若写在 `--- P1 ---` 之前，T6 不会捕获为旁白文本，Scene 1 内容偏移或缺失 | 确保开场白在 `--- P1 ---` 内部 |
| T6 合成后无法预览 | composition.html 内联 GSAP 库，浏览器直接打开报错/空白 | 打开 T6 自动生成的 index.html（无 GSAP 预览版） |
| T6 index.html 不刷新 | 旧代码 `if not exists` 导致后续 T6 不覆盖 | 已修：每次 T6 都生成无 GSAP 预览版到 index.html |
| Hero 封面 chips 受卡片控制 | 无卡片 = 纯封面无标签，有卡片 = 显示标签 | page-plans 设 `cards: []` 即可关闭 |

### T6 合成注意事项

- **脚本开头必须在 P1 内**：开场白必须放在 `--- P1 ---` 之后，否则 T6 不会捕获
- **T3 timeline 标题来自旁白首句**：T3 自动从每页口播正文首句（前 30 字）提取语义化标题，替代原来硬编码的 P1/P2；可通过 page-plans 覆盖
- **Hero chip-row 受卡片控制**：page-plans 设 `cards: []` 即可关闭封面标签
- **index.html = 可翻页预览版**：T6 生成两个文件——`06-composition.html`(有 GSAP，供 T7 渲染) 和 `index.html`(无 GSAP，有翻页导航和响应式缩放，浏览器直接打开)
- **timeline 标题不对齐**：手动改 timeline.json 标题时要确保与实际口播稿 P 标记内容匹配，避免 off-by-one
- **封面 chips 硬编码**：hero 布局固定添加 chip-row，需手动删除才有纯封面

### 修复顺序建议

注意 T2 门禁现在会自动校验口播稿开头是否在 P1 内，若未通过会提示退回修改。

合成问题通常是口播稿格式导致的，不要直接修 composition。修复顺序：
1. 先修口播稿（如移动开场白到 P1 内）
2. 重跑 T3（重新生成 timeline，更新各页时长）
3. 再跑 T6（生成新 composition + 预览）
4. 最后 T7 渲染

每一步跑完手动检查：
- T3 → `timeline.json` 各页时长合理吗？
- T6 → 打开 `index.html` 预览，Scene 标题/正文正确吗？
