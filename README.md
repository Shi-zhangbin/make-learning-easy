# Make Learning Easy 🚀

> AI 视频全自动生产线 — 从一句话到成品视频
> 专注于技术教程和知识科普内容
> 🧑‍💻 `codex/bilibili-video-making` 分支 — B站风格改造
> 🏃 `codex/bottom-progress-bar` 分支 — 底部进度条跑步小人

## 快速开始

```bash
# 安装依赖
node -v                     # 需要 Node.js 18+（HyperFrames 要求）
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入你的 key（wuyinkeji 配图 + 可选 Pexels/Pixabay 兜底）

# 一键全自动
bash go.sh create "2026-06-27_主题_[Codex]" --topic "..." --auto

# 分步控制
bash go.sh run --episode "2026-06-27_主题_[Codex]" --step T0
```

---

## B站风格 & 脱口秀模式（分支特色）

`codex/bilibili-video-making` 分支在主干基础上增加了整套 B站特色改造：

| 改造点 | 说明 |
|--------|------|
| **talk-show 设计预设** | 暖橙 `#FF6B35` + 青蓝 `#00C4FF`，大字冲击，适合脱口秀、程序员内容 |
| **T2 脱口秀脚本** | 提示词要求自嘲式程序员语气产出，翻车场景破题、段子穿插干货 |
| **T4 二次元分镜** | 配图描述指向漫画/梗图风格，程序员场景抽象夸张化表达 |
| **T5 配图风格化** | 根据预设自动追加风格前缀（bilibili→anime, talk-show→cartoon） |
| **T6 弹幕浮层** | 8条 B站弹幕 CSS 浮动动画（"学到了"、"下次一定"等） |
| **吐槽气泡** | 支持 `speech-bubble` 元素类型，画面中插入对话气泡 |
| **代码标签** | 代码块右上角自动生成语言标签 |

使用方式：
```bash
git switch codex/bilibili-video-making
python3 -m core.engine init "2026-06-27_主题_[Codex]" --topic "..." --style talk-show
```

可选风格：
```bash
python3 -m core.engine init "2026-06-27_主题_[Codex]" --topic "..." --style bilibili   # 默认，二次元粉
python3 -m core.engine init "2026-06-27_主题_[Codex]" --topic "..." --style dark-teal  # 深色科技
# 全部预设: bash go.sh designs
```

---

## 管线流程

```
T0(选题) → T1(大纲) → T2(口播稿) → T3(配音+字幕) → T4(分镜) → T5(配图) → T6(Composition) → T7(渲染)
```

为什么T2在T4之前？先写口播稿 → 生成真实TTS音频 → 实测每段时长 → 再按真实时长设计分镜。
这样每页停留时间与口播长度精确匹配，不会出现"画面翻过去了话还没说完"的问题。

| 步骤 | 说明 | 自动化 |
|------|------|--------|
| T0 | AI agent 写选题报告 | 自动委托 |
| T1 | AI agent 写知识点大纲 | 自动委托 |
| T2 | AI agent 写口播稿 | 自动委托 |
| T3 | edge-tts 配音 + whisper 字幕 | ✅ 全自动 |
| T4 | AI agent 设计分镜方案 | 自动委托 |
| T5 | 三级 fallback 配图生成 | ✅ 全自动 |
| **T6** | **元素驱动 HyperFrames 引擎** | ✅ 全自动 + 门禁 |
| T7 | HyperFrames 渲染 + 音视频合成 | ✅ 全自动 |

---

## 核心能力

### 🎬 HyperFrames 渲染引擎

所有场景合成一个 HTML 文件，通过 HyperFrames 渲染为 MP4：

- **Push Slide 过渡** — 场景之间平滑推入，不是跳切
- **逐元素 GSAP 动画** — badge、标题、卡片、图片各有不同的入场方向和缓动曲线
- **呼吸光晕装饰** — 背景渐变呼吸，画面有层次感
- **TTS 语音同步** — edge-tts 配音自动嵌入视频
- **弹幕浮层 (分支)** — 画面叠加动态 B站弹幕
- **🏃 底部进度条跑步小人** — AI 生成的精灵图角色在进度条上奔跑

### 🏃 进度条跑步小人

视频底部进度条上有一个 **AI 生成的小角色在奔跑**，自身做帧动画，位置随视频进度从左到右推进。

**预制风格：**

| 预设 | 形象 | 使用 |
|------|------|------|
| 🦕 **dino**（默认） | 小蓝恐龙，Q版像素风 | `pipeline-state.json` 中设置 `"sprite_style": "dino"` |
| 🧒 **boy** | 小男孩，chibi 风 | `pipeline-state.json` 中设置 `"sprite_style": "boy"` |

**技术实现：**

- 3×3 网格 AI 生成 → 自动去底 → 内容居中 → 拼接成 9 帧水平 strip（540×60px）
- GSAP onUpdate 逐帧驱动，与 HyperFrames 渲染同步（1.2s/循环）
- 每帧独立做视觉中心对齐，避免角色跳动
- 支持扩展：在 `core/sprite_runner.py` 的 `SPRITE_PRESETS` 字典加条目即可新增风格

**手动生成精灵图：**
```bash
python3 -m core.sprite_runner preset --style dino --out sprites/runner.png   # 小恐龙
python3 -m core.sprite_runner preset --style boy --out sprites/runner.png    # 小男孩
```

### 🧩 元素驱动布局

没有固定布局模板。每个场景是一个元素数组，自由组合：

```json
{
  "elements": [
    {"type": "badge", "text": "01 · 核心概念"},
    {"type": "heading", "text": "标题", "size": "xl"},
    {"type": "card-row", "cards": [
      {"icon": ":brain:", "title": "卡片一", "body": "描述"},
      {"icon": ":zap:", "title": "卡片二", "body": "描述"}
    ]},
    {"type": "image", "src": "data:image/...", "size": "large"}
  ]
}
```

支持的 15 种元素类型：`badge`、`heading`(xl/lg/md/sm)、`paragraph`(lg/md/sm)、`card-row`、`card-alt`、`card-alt-row`、`grid-2x2`、`image`(small/medium/large/fill)、`split`、`code`、`fq-row`、`quote`、`chip-row`、`button`、`speech-bubble`(**分支**)、`accent-line`、`spacer`。

### 🎨 设计预设系统

视频的颜色、字体、间距来自设计预设 YAML。换一个预设就换一套视觉风格，内容不用改。

内置 7+1 套预设：

| 预设 | 底色 | 强调色 | 来源 |
|------|------|--------|------|
| claude | 暖白 `#faf9f5` | 珊瑚 `#cc785c` | [Anthropic](https://claude.ai) |
| linear | 纯黑 `#010102` | 紫蓝 `#5e6ad2` | [Linear](https://linear.app) |
| mintlify | 白 `#ffffff` | 青 `#00d4a4` | [Mintlify](https://mintlify.com) |
| stripe | 白 `#ffffff` | 蓝紫 `#635bff` | [Stripe](https://stripe.com) |
| vercel | 白 `#ffffff` | 蓝 `#0070f3` | [Vercel](https://vercel.com) |
| dark-teal | 深灰 `#0A0C0E` | 青绿 `#4FC3A1` | 自定义 |
| bilibili | 浅灰 `#F5F6F7` | 粉 `#FB7299` | [Bilibili](https://bilibili.com) |
| **talk-show** (分支) | 浅灰 `#F0F2F5` | 暖橙 `#FF6B35` | 程序员脱口秀风格 |

---

## 项目结构

```
.
├── go.sh                  # 主入口：run / create / status / list / designs
├── AGENTS.md              # Agent 与开发者协作准则
├── core/
│   ├── engine.py          # 管线编排引擎
│   ├── config.py          # 配置
│   ├── agent_steps.py     # Agent 内容生成提示词（分支含脱口秀/二次元指导）
│   ├── imagegen.py        # 三级配图生成（分支含风格前缀）
│   ├── subtitle.py        # 字幕处理
│   ├── steps/
│   │   ├── t6_compositions.py  # 元素驱动 HyperFrames 引擎（分支含弹幕/气泡）
│   │   ├── tts.py              # edge-tts 配音 + 字幕
│   │   └── t7_render.py        # HyperFrames 渲染
│   ├── gates/
│   │   └── gate_master.py  # 门禁检查器
│   ├── designs/
│   │   ├── base.py             # 设计预设加载器
│   │   └── presets/*.yaml      # 7+1 套设计预设（分支含 talk-show）
│   ├── sprite_runner.py      # 精灵图生成 + 预处理管线（dino/boy 预设）
│   └── assets/
│       ├── gsap.min.js       # 本地化的 GSAP 动画库
│       ├── sprite_runner.png # 默认跑步精灵（小恐龙）
│       └── sprite_dino.png   # 小恐龙精灵（独立文件）
├── episodes/               # 每期视频的内容目录
│   └── 2026-06-27_主题_[Codex]/
│       ├── timeline.json   # 元素数组 + 时长
│       ├── 配音稿_分段.txt # 口播稿
│       ├── audio/          # TTS 音频 + .srt/.ass 字幕
│       ├── images/         # AI 配图 + b64_cache
│       ├── 成品/           # 最终 MP4
│       └── renders/        # 渲染临时文件
└── skills/                 # Agent 技能文件
```

---

## 创建新期目

```bash
# 完整管线
bash go.sh create --name "第7期_主题" --topic "用通俗方式讲 Transformer" --auto

# 分步控制
bash go.sh run --episode "2026-06-27_主题_[Codex]" --step T0

# Agent 步骤（T0/T1/T2/T4）:
# 1. engine 输出 "需要生成" 提示
# 2. 读取 .step_prompt.json 获取 topic/outline/script
# 3. 按 skills/ascend-video-pipeline.md 生成内容
# 4. 写入输出文件，删除 .step_prompt.json
# 5. 重新执行该步骤，门禁通过后自动推进

# 查看状态
bash go.sh status --episode "2026-06-27_主题_[Codex]"
bash go.sh list
bash go.sh designs

# 切换 B站风格分支
git switch codex/bilibili-video-making
```

---

## 设计预设参考

设计预设的设计 tokens 来源于 [awesome-design-md](https://github.com/awesome-design-md)，一个收集各大品牌设计系统的开源项目。分支预设 talk-show 为自定义设计，基于 B站 bilibili 预设改造。

## 致谢

| 项目 | 作者 | 说明 |
|------|------|------|
| [HyperFrames](https://hyperframes.heygen.com) | HeyGen | HTML 视频渲染引擎 |
| [edge-tts](https://github.com/rany2/edge-tts) | rany2 | 微软 Edge TTS 封装 |
| [whisper.cpp](https://github.com/ggerganov/whisper.cpp) | ggerganov | 本地语音识别 |
| [awesome-design-md](https://github.com/awesome-design-md) | 社区 | 品牌设计系统分析文档 |
| [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | harry0703 | 字幕与图片搜索方案参考 |

## 许可

MIT License
