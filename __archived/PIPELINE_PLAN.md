# ascend-pipeline — 融合管线规划

> 统一 B站视频管线、HyperFrames、开源素材的 **AI视频全自动生产线**
> 仓库：`~/Desktop/ascend-pipeline/`

---

## 一、总览

### 管线定位
融合三项技术栈：
1. **B站视频管线** — 多agent协作范式 + 审计/校验/门禁
2. **HyperFrames** — 动画渲染引擎（composition → timeline → 视频帧）
3. **开源素材** — 现实场景图片搜刮（替代纯AI生成，提升真实感）

### 核心原则（从原管线继承）
- AGENTS.md 是唯一真相源
- 多agent独立profile，不跳过任何agent
- delegate_task 必须带 checklist
- 三段式门禁：开工前 → 渲染前 → 交付前
- 口播先行（T3→TTS→T2）

---

## 二、工作流全景（T0–T8）

```
T0 ──→ T1 ──→ T3 ──→ TTS ──→ T2 ──→ T4+T5 ──→ T6 ──→ T7 ──→ T8
选题   知识点   口播稿   实测    PPT大纲+   素材搜刮   HyperFrames  渲染+  字幕
研究   大纲     先行     时长    分镜设计    +AI配图   compositions  配音   (按需)
```

### T0 – 选题研究
**执行者:** `xuan-ti-yan-jiu-yuan` (deepseek-v4-pro)
**产出:** 选题范围定义、竞品分析、主对比策略
**门禁:** 主人确认选题后再推进

### T1 – 知识点大纲
**执行者:** `yanjiuyuan` (deepseek-v4-pro)
**产出:** 结构化知识大纲（含代码示例点、踩坑点）
**门禁:** 主人审核大纲质量

### T3 – 口播稿（首位！）
**执行者:** `bianju` (MiniMax-M2.7)
**产出:** 完整口播稿.txt（纯文字，无 ## 无 ** 标记）
**门禁:** 主人审核语言风格

### TTS – 实测时长
**执行者:** 启明（机械执行）
**命令:** `python3 -m edge_tts --voice zh-CN-XiaoxiaoNeural -f 口播稿.txt --write-media 口播稿.mp3`
**后处理:** `atempo=1.15,volume=6dB` → `ffprobe` 实测每段时长
**产出:** 时间线基准（确定每页停留秒数）

### T2 – PPT大纲 + 分镜设计
**执行者:** `meishu` (MiniMax-M2.7)
**输入:** 口播稿 + TTS实测时长 + 已选设计风格
**产出:**
- **PPT大纲.md** — 每页布局类型、元素清单、卡片文字
- **timeline.json** — 每页 id/start/end/duration/narration
- **image_slots.json** — 每页配图需求（source=real/ai/code）
**门禁:** 主人审核分镜方案

### T4 – 现实素材搜刮
**执行者:** 启明（Python脚本直管，非独立agent）
**技能:**
- web_search → 图片URL下载（Unsplash / Pixabay / Bing Image）
- SVG/图标库（Feather Icons / Heroicons）
**产出:** 下载到 `episodes/第N期/素材/真实图片/`

### T5 – AI配图生成
**执行者:** `chuangzuo` (terminal background)
**引擎:** wuyinkeji API / ComfyUI(SDXL)
**产出:** 下载到 `episodes/第N期/素材/AI图片/`

### T6 – Composition 生成
**执行者:** `editor` (qwen3.6-plus via delegate_task)
**输入:** PPT大纲 + timeline + 图片素材
**产出:** 每页一个 composition HTML（含 GSAP timeline + base64内联图）
**门禁:**
- ✅ 所有图片base64内联
- ✅ GSAP timeline 注册到 window.__timelines["s{id}"]
- ✅ 每页暴露 window.__hf["s{id}"] = {duration, seek}
- ✅ 相邻页布局不同
- ✅ 字体 sans-serif
- ✅ 右下角页码

### T7 – 渲染 + 配音合成
**执行者:** 启明 + hyperframes-producer
**命令:**
```bash
cd episodes/第N期 && hyperframes render . --fps 15 -o final.mp4
ffmpeg -i final.mp4 -i 配音_加速.mp3 -c:v copy -c:a aac -b:a 192k final_有声.mp4
```
**门禁:** 渲染前 `harness.py phase2` 全绿

### T8 – 字幕（按需）
**执行者:** `zimu-agent` (deepseek-v4-flash)
**格式:** ASS（白字+黑描边+分页锚定法）
**封装:** MKV

---

## 三、HyperFrames 深度集成

### 3.1 Composition 架构
```
episodes/第N期/
├── index.html          # 总时间线（引用所有composition）
├── compositions/
│   ├── scene_1.html    # 第1页composition
│   ├── scene_2.html
│   └── ...
├── 素材/
│   ├── 真实图片/       # T4产出
│   └── AI图片/         # T5产出
├── 口播稿.txt          # T3产出
├── PPT大纲.md           # T2产出
├── timeline.json        # T2产出
└── .design-system       # 设计风格标记
```

### 3.2 时间线格式
```html
<div id="root" data-composition-id="main" data-start="0" data-duration="141.0" data-width="1920" data-height="1080">
  <div data-composition-id="s1" data-composition-src="compositions/scene_1.html" data-start="0.00" data-duration="10.0"></div>
  <div data-composition-id="s2" data-composition-src="compositions/scene_2.html" data-start="10.00" data-duration="8.5"></div>
  ...
</div>
```

### 3.3 布局轮换库（10种）
| # | 布局 | 适用场景 |
|---|------|---------|
| 1 | hero | 封面/过渡页 |
| 2 | standard-concept | 左文右图 |
| 3 | flipped-concept | 左图右文 |
| 4 | comparison | 双栏对比 |
| 5 | data-chart | 数据图表 |
| 6 | flowchart | 流程图/SVG |
| 7 | quote-definition | 居中引用 |
| 8 | card-grid | 多卡片网格 |
| 9 | timeline-h | 时间轴 |
| 10 | code-block | 深色代码块 |

---

## 四、多Agent协作范式

### 4.1 Profile 架构
```
启明 (主协调者)
├── xuan-ti-yan-jiu-yuan (T0)
├── yanjiuyuan (T1)
├── bianju (T3)
├── meishu (T2)
├── chuangzuo (T5)
├── editor (T6)
├── shenheyuan (审计)
└── zimu-agent (T8, 按需)
```
**T4 和 T7 由启明直管**（不需要独立思考，机械执行）

### 4.2 协作协议
1. **启明分解任务** → 在Kanban创建任务链
2. **委托agent** → delegate_task 必须在 context 开头贴 checklist
3. **agent 产出** → 写入 episodes/第N期/ 对应目录
4. **shenheyuan 审计** → 每个 agent 产出后，shenheyuan 做格式/规范检查
5. **主人审核** → 关键节点通知主人确认（口播稿、分镜、最终效果）

### 4.3 审核触发点
```
T0完成 → 主人确认选题
T1完成 → 主人确认大纲
T3完成 → 飞书通知主人审核口播稿
T2完成 → 飞书通知主人审核分镜
T6完成 → 启明做规范审计（harness.py phase2）
T7完成 → 主人审核最终视频效果
T8完成 → 交付完成
```

---

## 五、开源素材（现实图片搜刮）

### 5.1 融合方案
| 来源 | 用途 | 集成方式 |
|------|------|---------|
| Unsplash API | 场景/建筑/人物 | web_search → 下载 → base64 |
| Pixabay API | 科普/自然/科技 | web_search → 下载 → base64 |
| Bing Image | 特定概念图 | web_search → 下载 → base64 |
| SVG icons | UI图标/标注 | 内置到composition（无base64） |
| AI配图(SDXL) | 架构图/流程图/概念示意 | ComfyUI API → base64 |

### 5.2 选择策略（在 image_slots.json 定义）
```json
{
  "page": "s3",
  "slot": "main",
  "content": "华为云昇腾服务器实物图",
  "source": "real",        // real / ai / code
  "fallback_svg": true    // 搜刮失败时用SVG占位
}
```
- **real** → T4 搜索现实图片
- **ai** → T5 AI生成
- **code** → 不需要图（代码页）

### 5.3 降级方案
搜刮失败 → SVG占位（内置在composition中，不依赖外部资源）

---

## 六、质量门禁（三段式）

### 6.1 Phase 1 – 开工前
```bash
python3 scripts/harness.py episodes/第N期_xxx 1
```
- ✅ AGENTS.md 存在
- ✅ 设计风格已选（.design-system）
- ✅ 口播稿已写
- ⏹️ 人工确认：profile存在、API可用、语速参数

### 6.2 Phase 2 – 渲染前
```bash
python3 scripts/harness.py episodes/第N期_xxx 2
```
- ✅ index.html + compositions/ 存在
- ✅ 时间线连续无间隙
- ✅ 每个composition规范正确（14项检查）
- ✅ hyperframes lint 0 error
- ❌ 任何一项不通过 → 不得渲染

### 6.3 Phase 3 – 交付前
```bash
python3 scripts/harness.py episodes/第N期_xxx 3
```
- ✅ 视频文件存在
- ✅ 视频长度 > 10s
- ✅ 包含音频流

---

## 七、第一期复盘 → 第二期修复清单

### 7.1 第1期合规性问题（已复盘）
| # | 问题 | 严重度 | 第2期修复 |
|---|------|--------|----------|
| 1 | 跳过所有agent，启明自己写全部代码 | P0 | ✅ 按T0-T8委托agent |
| 2 | 未跑开工清单 | P0 | ✅ 跑harness phase1 |
| 3 | 口播先于PPT，但分镜对齐不是独立步骤 | P1 | ✅ T2输出含分镜对齐 |
| 4 | 未用HyperFrames block（手写CSS排版） | P1 | ✅ T6 editor生成 |
| 5 | 未在delegate_task带checklist | P0 | ✅ context开头贴checklist |
| 6 | 没有Kanban任务链 | P1 | ✅ 每期建Kanban |
| 7 | 忘记font-family（汉字消失） | P0 | ✅ checklist铁律 |
| 8 | 缺完整验证流程 | P1 | ✅ phase2门禁 |

### 7.2 第2期新增改进（融合开源素材）
| # | 改进 | 说明 |
|---|------|------|
| 1 | T4搜刮现实图片 | 替代部分AI配图，提升真实感 |
| 2 | 10种布局轮换 | 不再只有Mintlify通用布局 |
| 3 | image_slots.json | 每页配图需求结构化定义 |
| 4 | 降级SVG方案 | API不可用时自动退路 |
| 5 | 审计agent介入 | shenheyuan做格式检查 |

---

## 八、使用方式

### 8.1 开启新一期
```bash
# 1. 创建目录
mkdir -p episodes/第N期_标题/素材/{真实图片,AI图片} compositions

# 2. 选择设计风格
cp designs/awesome-design-md/design-md/mintlify/DESIGN.md episodes/第N期_标题/
echo "mintlify" > episodes/第N期_标题/.design-system

# 3. 跑开工门禁
python3 scripts/harness.py episodes/第N期_标题 1
```

### 8.2 生产流程（启明自动执行）
```
T0(选题) → T1(大纲) → T3(口播) → TTS实测 → T2(分镜)
→ T4(搜图) + T5(AI配图) → T6(composition) → phase2门禁
→ T7(渲染+配音) → phase3门禁 → T8(字幕) → 交付
```

### 8.3 设计风格切换
每期可以从 awesome-design-md 的75种风格中选3种，主人确认1种后固化到 `.design-system`。

---

## 九、roadmap

| 阶段 | 内容 | 状态 |
|------|------|------|
| v1.0 | 基础管线建立（第1期复盘完成） | ✅ |
| v1.1 | 融合开源素材（T4搜刮） | 🔜 第2期 |
| v1.2 | Profile全部创建+Kanban自动化 | 🔜 第2期前 |
| v1.5 | 审计agent介入（shenheyuan） | 📋 规划中 |
| v2.0 | 全自动无人工介入（主人仅审核关键节点） | 🎯 目标 |
