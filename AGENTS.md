 # Make Learning Easy — Agent & Developer Handbook
 
 > 本文件供运行此项目的所有 AI Agent（Codex、Claude Code、Hermes 等）以及人类开发者共同遵守。每次开始任务前必须先读取。
 > 会同步到 GitHub 仓库，作为项目公开文档的一部分。
 
 ---
 
 ## 项目定位
 
 这是一个 **AI 视频自动生产线**。输入一个主题，走完 T0→T7 管线，产出成品 MP4 视频。
 
 - **管线入口**: `bash go.sh`
 - **引擎代码**: `core/engine.py`
 - **期目目录**: `episodes/YYYY-MM-DD_主题_-Agent/`
 - **设计预设**: `core/designs/presets/` (7 套)
 - **主语言**: Python 3.14+, Node.js (HyperFrames)
 
 
## 命名规范 — 统一期目 & 文件命名

所有 agent（Codex / Claude Code / Hermes）必须遵循同一命名规范，以便横向对比。

### 期目目录命名

```
YYYY-MM-DD_主题_-Agent
```

示例: `2026-06-26_云服务的前世今生_-Codex`

- **日期前缀**: 按时间排序，快速定位近期产出
- **主题居中**: 一眼识别内容
- **Agent 后缀**: 区分制作者，方便同主题对比
- Agent 可选值: `Claude-Code`, `Codex`, `Hermes`
- 统一命名格式 `YYYY-MM-DD_主题_-Agent`

### 期目内部文件

每个期目使用 **步骤序号 + 语义名** 的统一格式。所有文件名在 `core/config.py` 的 `FILE_NAMES` 中定义。

```
00-topic.md                ← T0 选题报告
01-outline.md              ← T1 知识点大纲
02-script.txt              ← T2 口播稿
03-audio/narration.mp3     ← T3 TTS 产物
03-timeline.json           ← T3 时间线
04-storyboard.md           ← T4 分镜方案
04-image-slots.json        ← T4 配图需求
05-images/                 ← T5 AI 配图
06-composition.html        ← T6 合成结果 (HyperFrames 入口)
07-final/final.mp4         ← T7 最终视频
pipeline-state.json        ← 管线状态
.agent.json                ← agent 元数据
```

注: `compositions/` 和 `renders/` 由 HyperFrames 外部引擎管理，不在 FILE_NAMES 中。

### Agent 元数据

每个期目根目录下的 `.agent.json` 记录制作者信息：

```json
{
  "agent": "Codex",
  "engine": "core",
  "created": "2026-06-26T10:00:00",
  "topic": "...",
  "design_style": "bilibili"
}
```

### 创建新期目

```bash
python3 -m core.engine init "2026-06-26_主题_-Agent" --topic "..." --style bilibili
```

## 快速开始
 
 ```bash
 # 创建新期目
 python3 -m core.engine init "YYYY-MM-DD_主题_-Agent" --topic "..." --style bilibili
 
 # 查看已创建期目
 bash go.sh list
 
 # 查看期目状态
 bash go.sh status --episode "YYYY-MM-DD_主题_-Agent"
 
 # 运行单个步骤
 bash go.sh run --episode "YYYY-MM-DD_主题_-Agent" --step T0
 
 # 查看可用的设计预设
 bash go.sh designs
 ```
 
 ## 管线总览
 
 ```
 T0 → T1 → T2 → T3 → T4 → T5 → T6 → T7
 (选题) (大纲) (口播稿) (配音) (分镜) (配图) (合成) (渲染)
 ```
 
 | 步骤 | 执行者 | 产出 | 说明 |
 |------|--------|------|------|
 | T0 | Agent | 选题研究报告.md | 选题背景、核心知识点(5-8)、教学类比(2-3)、讲解路径、常见误区 |
 | T1 | Agent | 知识点大纲.md | 4-7 章节，一、二、三编号 |
 | T2 | Agent | 配音稿_分段.txt | 5-8 页，口语化，正文无 ## ** `` |
 | T3 | 自动 | narration.mp3/.srt/.ass + timeline.json | 用 edge-tts |
 | T4 | Agent | PPT大纲.md + image_slots.json | 每页布局 + 配图需求 |
 | T5 | 自动 | 9 张 AI 配图 | 走 wuyinkeji/pexels/pixabay/SVG 兜链条 |
 | T6 | 自动 | index.html | 元素驱动合成，dark-teal 或 bilibili 风格 |
 | T7 | 自动 | 成品/final.mp4 | HyperFrames 渲染 + 音轨混合 |
 
 > **Agent 步骤规范**: Agent 步骤（T0/T1/T2/T4）产出文件后，删除 `.step_prompt.json`，重新运行同一步骤通过门禁后，引擎自动推进到下一步。
 
 ## 设计预设
 
 可用 7 套预设，通过 `bash go.sh designs` 查看最新列表：
 
 | 预设名 | 底色 | 强调色 | 风格描述 |
 |--------|------|--------|---------|
 | bilibili | 浅灰 `#F5F6F7` | 粉 `#FB7299` | B站二次元科技，默认风格 |
 | claude | 暖白 `#faf9f5` | 珊瑚 `#cc785c` | 暖色人文 |
 | dark-teal | 深灰 `#0A0C0E` | 青绿 `#4FC3A1` | 深色科技 |
 | linear | 纯黑 `#010102` | 紫蓝 `#5e6ad2` | 深色极简 |
 | mintlify | 白 `#ffffff` | 青 `#00d4a4` | 清爽文档 |
 | stripe | 白 `#ffffff` | 蓝紫 `#635bff` | 金融专业 |
 | vercel | 白 `#ffffff` | 蓝 `#0070f3` | 黑白极简 |
 
 ## 核心规则（红线）
 
 以下规则对所有 Agent 强制执行。每条附带**遵守示例**和**违规示例**。
 
 ### 规则 1：默认使用 bilibili 风格
 
 除非用户**明确指定**其他风格，创建期目时一律 `--style bilibili`。
 
 ✅ **遵守示例**
 ```bash
 python3 -m core.engine init "2026-06-27_Docker入门_-Claude-Code" --topic "..." --style bilibili
 ```

 ❌ **违规示例**
 ```bash
 python3 -m core.engine init "2026-06-27_Docker入门_-Claude-Code" --topic "..." --style dark-teal
 # 擅自选择非默认风格，需要用户明确要求才能这样做
 ```
 
 ### 规则 2：严格执行视频时长要求
 
 用户要求"不少于 X 分钟"时，必须量化校验，不可自行"合理裁剪"。
 
 校验方式：T2 口播稿写完后，用 `core/config.py` 中的 `TTS_EFFECTIVE_CHARS_PER_SEC = 4.2` 估算音频时长：
 
 ```
 预估秒数 = 配音稿有效字符数 / 4.2
 目标秒数 = 用户要求的最低分钟数 × 60
 ```
 
 如果 `预估秒数 < 目标秒数 × 0.85`（留 15% 余量给实际 TTS 语速偏差），必须回 T2 加内容。
 
 ✅ **遵守示例**
 ```
 用户要求：10-15 分钟
 T2 写完 12 分钟的稿子（≈ 3000-4000 有效字符按 4.2 字/秒估算）
 校验：3950 / 4.2 = 940s ≈ 15.6min > 10min ✅
 ```
 
 ❌ **违规示例**
 ```
 用户要求：10 分钟以上
 Agent 觉得"内容够了"自行压缩到 7.5 分钟
 没有做任何估算校验就推进
 ```
 
 ### 规则 3：禁止输出占位符内容
 
 所有生成的内容文件（配音稿、PPT大纲、image_slots、配图描述）必须写入**实际可用内容**。
 
 ✅ **遵守示例**
 ```
 配图描述："IBM大型机与终端机的历史场景，1960年代风格"
 ```
 
 ❌ **违规示例**
 ```
 配图描述：""（留空）或"图片"或"此处插入一张图片"或"图表占位"
 ```
 
 以下是占位符关键词检测列表（各 Agent 的输出都会被 `gate_master.py` 扫描匹配）：
 
 ```
 卡片 | 图片 | 图表 | TKTK | TODO | 占位 | placeholder
 此处插入 | 这里放 | 请插入 | 示例文本
 ```
 
 ### 规则 4：配音稿必须纯口播文字

`02-script.txt` 是直接喂给 TTS 配音引擎的，**只能包含口播文字**。不得包含：
- 元数据行（如 `音频配音稿 — xxx`、`目标时长：X 分钟`）
- 舞台指示（如 `（开场）`、`（停顿）`、`（完）`）
- 章节标题（如 `一、B站的前世今生`、`二、创始人`）
- 分隔线（如 `===`、`---`）

如果需标记分段，使用 `--- P1` 格式（仅 `core/steps/tts.py` 能识别的分页标记）。

✅ **遵守示例**
```
（文件内容第一行就是口播正文）
前两天我在工位上改一个祖传 bug，改到怀疑人生...
...（全文只有口播文字）
```

❌ **违规示例**
```
音频配音稿 — 走进B站
目标时长：10分钟

===
（开场）
...正文内容...
（停顿）
---
二、下一章
...
```

### 规则 5：只处理用户指定的期目
 
 不要扫描 `episodes/` 目录做推测性工作。只创建/修改用户明确要求的那一期。
 
 ✅ **遵守示例**
 ```
 用户：做第10期
 Agent：只操作 episodes/第10期_xxx/
 看到 episodes/ 下有第1-9期，不碰
 ```
 
 ❌ **违规示例**
 ```
 用户：做第10期
 Agent：看到 episodes/下还有第3期选题规划_待定，顺手也做了
 产生非目标期目，浪费 token 和渲染时间
 ```
 
 ### 规则 6：所有产出必须在期目目录内
 
 不允许向 `episodes/` 根目录、仓库根目录或 `core/` 引擎目录写入任何文件。
 
 ✅ **遵守示例**
 ```
 episodes/第10期_云服务的前世今生/
 ├── 选题研究报告.md       ✅
 ├── audio/               ✅
 ├── images/              ✅
 └── 成品/final.mp4       ✅
 ```
 
 ❌ **违规示例**
 ```
 episodes/bilibili_preview.html   ❌ 放在期目目录外
 episodes/sprite_sheet.png        ❌ 放在期目目录外
 ```
 
## 已知风险

以下是管线当前已知的限制。所有人（Agent 和开发者）在遇到异常时应优先查阅此清单。

| 风险 | 影响 | 当前处理 |
|------|------|---------|
| **T2 开头文本丢失** | 口播稿开头若写在 `--- P1 ---` 之前，不会被任何 slide 捕获为旁白文本，导致 Scene 1 内容偏移或缺失 | 确保开场白在 `--- P1 ---` 内部。若需修复：将开头文本移入 P1 后重跑 T3→T6→T7 |
| **T6 合成后不可预览** | 06-composition.html 内联了 GSAP 库(约 15K 行)，浏览器打开时空白或报错，无法直接预览 | 已修(2026-06-29): T6 自动生成 index.html（无 GSAP，所有场景 opacity:1）。打开 index.html 即可静态预览 |
| **T3 timeline 标题来自旁白首句** | T3 自动从每页口播正文首句（前 30 字）提取语义化标题，替代原来硬编码的 P1/P2 | 首句可能不语义化（如"但是这里有一个问题"），可接受；若需更好标题可通过 02-page-plans.json 覆盖 |
| **Hero chip-row 受卡片控制** | 封面页的「入门科普/程序员日常/10分钟」标签只在有卡片内容时显示 | 无卡片 = 纯封面无标签；page-plans 设 `cards: []` 即可关闭 |
| **T2 门禁校验 P1 开头** | 口播稿开头不能在 --- P1 --- 之前，否则 T6 不会捕获为 Slide 旁白 | 门禁自动拦截并提示移入 P1 内，退回 T2 修改 |
| **T6 index.html 不更新** | index.html 是副本，旧代码 `if not exists` 导致后续 T6 不覆盖，用户看到的是旧版 | 已修(2026-06-29): 移除存在检查，index.html 现为无 GSAP 预览版，每次 T6 都会刷新 |
| **Hero 布局硬编码 chip-row** | `_page_spec_to_elements` 对 hero 布局固定添加 `["入门科普", "程序员日常", "10分钟"]` 标签，page-plans 无法关闭 | 若需纯封面（无标签）：在 composition.html 中手动删除 `<div class="chip-row">...`，然后重跑 T7 |
| **T7 渲染慢** | GSAP + HyperFrames 的 `Runtime.callFunctionOn` 在对长视频（>5min）并行帧采集时可能超时，降级到单 worker | 已修 `dur`→`duration` 缓解（2026-06-25）。如需观察渲染过程，可设置 `--headless=false` |
| **字幕烧录受限** | 中文路径下 ffmpeg 的 `subtitles` filter 可能不可用（Homebrew 默认不含 libass） | 字幕以独立 .srt/.ass 文件存放在 `audio/` 目录。如需烧录：`brew install ffmpeg-full` |
| **图片留白** | 容器内图片使用 `object-fit: contain`，宽高比不符时会产生暗色留白 | 属于有意行为，保证图片不被裁剪。如需填满可改为 `cover` |
 | **配图质量** | 默认 JPEG 压缩（-q:v 3）下图片约 50-80KB | 可在 `core/config.py` 中调大 `IMAGE_JPEG_QUALITY` |
 | **HyperFrames 闭源** | 渲染引擎是 proprietary npm 包（0.7.6），核心逻辑不可修改 | 如遇到阻断性 Bug，可考虑用 Playwright 替代 T7 |
| **T6 入场动画单一** | 所有元素使用统一入场方向（全向上淡入），视觉单调 | 已修 (2026-06-25): 3 种动画变体按页面+索引确定性分配，每元素从 y/x/scale 三类效果中轮换 |
| **视觉层次不足** | 纯平铺背景，缺乏深度感 | 已修 (2026-06-25): 增加环境浮点粒子 + 暗角渐变叠加层，增强视觉层次 |

## T6 合成注意事项

### 1. 脚本开头必须在 P1 内

T2 口播稿的**开场白文本（如 "前两天我在公司改一个祖传bug..."）必须放在 `--- P1 ---` 之后**。如果写在第一个 P 标记之前，`build_pagespec` 的 narration 提取正则（`---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)`）不会捕获这段文字，Scene 1 的开场白就丢了。

✅ 正确写法：
```
--- P1 ---
前两天我在公司改一个祖传bug，改到emo了...

今天我打算用一期视频的时间...

首先得聊一个最基本的问题：大模型的"食物"是什么？
--- P2 ---
```

❌ 错误写法：
```
前两天我在公司改一个祖传bug，改到emo了...
← 这行不在任何 P 标记内，被 T6 忽略

--- P1 ---
首先得聊一个最基本的问题：大模型的"食物"是什么？
```

### 2. index.html 可翻页预览（无 GSAP）

T6 会生成两个文件：

| 文件 | 用途 | 特点 |
|------|------|------|
| `06-composition.html` | T7 渲染用 | 有 GSAP 动画库，浏览器直接打开可能报错/空白 |
| `index.html` | 人工预览用 | 无 GSAP、无动画脚本、有翻页导航栏和响应式缩放，浏览器可直接打开浏览所有幻灯片 |

**预览版操作：**
- ◀ ▶ 按钮或 ← → 方向键翻页
- 空格键 / 点击画面进入下一页
- 右下角显示当前页码（如 3/8）
- 自动缩放适配窗口大小（1920×1080 → 浏览器视口）

任何时候想预览合成效果，打开 `index.html` 即可，无需等 T7 渲染。每次 T6 重跑后 `index.html` 自动刷新。

### 3. timeline.json 标题 vs 实际内容

timeline.json 的 `title` 字段决定了 Scene 标题。手动修改时要确保与**实际口播稿中的 P 标记内容**对齐，否则会出现标题和正文不匹配的 off-by-one。

### 4. 封面的 chip 标签

Hero 布局现在只在有卡片内容的页面显示 chip-row（`入门科普 / 程序员日常 / 10分钟`）。规则：
- **页面无卡片**（如纯封面）→ 自动隐藏 chip-row
- **页面有卡片**（如内容页）→ 显示 chip-row
- page-plans 设 `"cards": []` 即可关闭封面标签

---

*最后更新：2026-06-29*
*本文件与 [02-Bug与待修复清单.md](obsidian://open?vault=史章斌的远程仓库&file=10-职业发展%2F05-项目经验%2Fmake%20learning%20easy%2F02-Bug与待修复清单.md) 和 [06-方案对比与社区调研.md](obsidian://open?vault=史章斌的远程仓库&file=10-职业发展%2F05-项目经验%2Fmake%20learning%20easy%2F06-方案对比与社区调研.md) 同步更新。*
 
 ## 项目结构
 
 ```
 make-learning-easy/
 ├── AGENTS.md              # ← 本文件，Agent 和人共读
 ├── go.sh                  # 管线入口脚本
 ├── core/                    # 管线引擎
 │   ├── engine.py          # 核心调度
 │   ├── config.py          # 配置
 │   ├── agent_steps.py     # Agent 步骤 handler
 │   ├── gates/gate_master.py  # 门禁检查
 │   ├── steps/             # 各步骤实现
 │   │   ├── tts.py         # T3: 配音
 │   │   ├── t5_images.py   # T5: 配图
 │   │   ├── t6_compositions.py  # T6: 合成
 │   │   └── t7_render.py   # T7: 渲染
 │   ├── subtitle.py        # 字幕处理
 │   ├── pagespec.py        # 页面规格模型
 │   ├── designs/presets/   # 7 套设计预设 YAML
 │   └── assets/            # 静态资源（如 gsap.min.js）
 ├── episodes/              # 所有期目
 │   └── YYYY-MM-DD_主题_-Agent/
 │       ├── timeline.json
 │       ├── 配音稿_分段.txt
 │       ├── audio/         # TTS 产物
 │       ├── images/        # AI 配图
 │       └── 成品/          # 最终 MP4
 └── skills/                # 技能库（pipeline-rules 等）
 ```
 
 ## 常见流程
 
 ### 创建新期目
 
 ```bash
 python3 -m core.engine init "YYYY-MM-DD_主题_-Agent" --topic "..." --style bilibili
 ```
 
 ### 手动运行 Agent 步骤 (T0/T1/T2/T4)

 Agent 步骤需要你先写内容，再通过门禁：

 1. 运行步骤，引擎输出"需要生成"提示
 2. 读取 `.step_prompt.json` 获取 topic/outline/script 等信息（含 `validation_rules` 字段说明必须满足的条件）
 3. 按 `skills/ascend-video-pipeline.md` 生成内容
 4. 写入指定的输出文件
 5. **删除 `.step_prompt.json`**
 6. 重新执行同一步骤
 7. 门禁通过后自动推进到下一步

 ### 门禁反馈机制

 当门禁未通过时：
 1. 引擎在期目目录生成 `gate-feedback.json`，包含 `issues`（问题列表）和 `feedback_target`（退回步骤）
 2. `pipeline-state.json` 中该步骤标记为 `failed`
 3. 重新运行同一步骤时，Agent 应先读取 `gate-feedback.json` 了解错在哪里，再修复内容
 4. 修复后删除 `step-prompt.json` 重新运行
 5. 门禁通过后 `gate-feedback.json` 自动清理

 ### Pre-Condition 快速失败

 部分步骤在 `execute()` 执行前会运行 `pre_condition()` 检查前置条件。如果检查不通过，步骤会立即失败而不执行实际工作，节省 API 调用和时间。

 常见 pre-condition 失败：
 - **T3**: 脚本缺少 `--- P1` `--- P2` 分页标记（需要至少 2 个）
 - **T5**: `image_slots.json` 的 slot 缺少必填字段（filename/prompt/page/slot_index）
 - **T6**: `timeline.json` 只有不足 5 个 slide（脚本分页不足）
 - **T7**: composition HTML 不存在（需要先跑 T6）
 
 ### 查看渲染进度
 
 T7 渲染较长视频（>5min）时，可在 `renders/` 目录下观察进度：
 
 ```bash
 ls episodes/YYYY-MM-DD_主题_-Agent/renders/work-*/captured-frames/ | wc -l
 # 应能看到不断增长的数字，采集完毕后自动进入 FFmpeg 编码
 ```
 
 ### 在本地预览合成效果
 
 T6 完成后，可直接在浏览器打开 index.html 预览：
 
 ```bash
 open episodes/YYYY-MM-DD_主题_-Agent/index.html
 ```
 
 ---
 
 *最后更新：2026-06-25*
 *本文件与 [02-Bug与待修复清单.md](obsidian://open?vault=史章斌的远程仓库&file=10-职业发展%2F05-项目经验%2Fmake%20learning%20easy%2F02-Bug与待修复清单.md) 和 [06-方案对比与社区调研.md](obsidian://open?vault=史章斌的远程仓库&file=10-职业发展%2F05-项目经验%2Fmake%20learning%20easy%2F06-方案对比与社区调研.md) 同步更新。*

## 规则 7：执行类操作不问，直接跑

以下场景 **不需要询问用户同意**，直接执行：

- 管线步骤（T0-T7）的创建、运行、重试
- 长时间操作（渲染、图片生成）—— 异步跑，定期报进度
- 错误修复 —— 先自己修一轮，连续 3 次失败才停下说明
- 代码改动后的提交、推送、创建 PR

以下场景 **必须询问**：

- 涉及架构方向、设计取舍、产品定义的选择
- 不确定用户意图时澄清需求
