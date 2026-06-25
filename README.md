# Make Learning Easy 🚀

> AI 视频全自动生产线 — 从一句话到成品视频
> 专注于技术教程和知识科普内容

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入你的 key（wuyinkeji 配图 + 可选 Pexels/Pixabay 兜底）

# 一键全自动
bash go.sh create --name "第N期_主题" --topic "..." --auto
```

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

## 核心能力

### 🎬 HyperFrames 渲染引擎

所有场景合成一个 HTML 文件，通过 HyperFrames 渲染为 MP4：

- **Push Slide 过渡** — 场景之间平滑推入，不是跳切
- **逐元素 GSAP 动画** — badge、标题、卡片、图片各有不同的入场方向和缓动曲线
- **呼吸光晕装饰** — 背景渐变呼吸，画面有层次感
- **TTS 语音同步** — edge-tts 配音自动嵌入视频

### 🧩 元素驱动布局

没有固定布局模板。每个场景是一个元素数组，自由组合：

```json
{
  "elements": [
    {"type": "badge", "text": "01 · 核心概念"},
    {"type": "heading", "text": "标题", "size": "xl"},
    {"type": "card-row", "cards": [
      {"icon": "🧠", "title": "卡片一", "body": "描述"},
      {"icon": "⚡", "title": "卡片二", "body": "描述"}
    ]},
    {"type": "image", "src": "data:image/svg+xml;base64,...", "size": "large"}
  ]
}
```

支持的 14 种元素类型：`badge`、`heading`(xl/lg/md/sm)、`paragraph`(lg/md/sm)、`card-row`、`card-alt`、`card-alt-row`、`grid-2x2`、`image`(small/medium/large/fill)、`split`(左右分栏)、`code`(代码块)、`fq-row`、`quote`、`chip-row`、`button`、`accent-line`、`spacer`。

### 🎨 设计预设系统

视频的颜色、字体、间距来自设计预设 YAML。换一个预设就换一套视觉风格，内容不用改。

内置 7 套预设：

| 预设 | 底色 | 强调色 | 来源 |
|------|------|--------|------|
| claude | 暖白 `#faf9f5` | 珊瑚 `#cc785c` | [Anthropic](https://claude.ai) |
| linear | 纯黑 `#010102` | 紫蓝 `#5e6ad2` | [Linear](https://linear.app) |
| mintlify | 白 `#ffffff` | 青 `#00d4a4` | [Mintlify](https://mintlify.com) |
| stripe | 白 `#ffffff` | 蓝紫 `#635bff` | [Stripe](https://stripe.com) |
| vercel | 白 `#ffffff` | 蓝 `#0070f3` | [Vercel](https://vercel.com) |
| dark-teal | 深灰 `#0A0C0E` | 青绿 `#4FC3A1` | 自定义 |
| bilibili | 浅灰  | 粉  | [Bilibili](https://bilibili.com) |

## 项目结构

```
.
├── go.sh                  # 主入口：run / create / status / list / designs
├── v3/
│   ├── engine.py          # 管线编排引擎
│   ├── steps/
│   │   ├── t6_compositions.py  # 元素驱动 HyperFrames 引擎
│   │   ├── tts.py              # edge-tts 配音 + 字幕
│   │   └── t7_render.py        # HyperFrames 渲染
│   ├── designs/
│   │   ├── base.py             # 设计预设加载器
│   │   └── presets/*.yaml      # 7 套设计预设
│   └── templates/              # (废弃) 旧 Jinja2 模板
│       └── layouts/*.j2
├── episodes/               # 每期视频的内容目录
│   └── 第N期_主题/
│       ├── timeline.json   # 元素数组 + 时长
│       ├── 配音稿_分段.txt # 口播稿
│       ├── audio/          # TTS 生成的音频
│       ├── images/         # AI 生成的配图
│       └── renders/        # 渲染好的 MP4
└── .codex_instructions.md  # AI 编码规则（视频必须走管线）
```

## 创建新期目

```bash
# 完整管线
bash go.sh create --name "第7期_主题" --topic "用通俗方式讲 Transformer" --auto

# 查看状态
bash go.sh status --episode "第7期_神经网络训练技巧"

# 列出所有期目
bash go.sh list

# 查看可用设计预设
bash go.sh designs
```

## 设计预设参考

设计预设的设计 tokens 来源于 [awesome-design-md](https://github.com/awesome-design-md)，一个收集各大品牌设计系统的开源项目。

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
