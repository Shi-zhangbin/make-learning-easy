# 启明 v2.0 管线 — 全Agent强制规范

> 本文件是新管线的单一真相源。所有agent必须遵守。
> 旧管线存档：GitHub Shi-zhangbin/bilibili-video-pipeline
> 实验目录：`~/archive/启明实验_新管线/`

---

## §0. 工作流锚点顺序（不可改变）

### ⚠️ 铁律：delegate_task时必须携带AGENTS.md checklist
每次delegate_task给agent时，context开头必须包含对应的checklist，逐条列出。
没有checklist的delegate = 没有规则。agent不知道AGENTS.md存在。

例如T6 editor的delegate context开头必须写：
```
【AGENTS.md §5 T6 editor强制checklist — 逐条执行】
□ font-family: sans-serif（禁止PingFang SC等）
□ h2: 54px（不是36px）
□ 卡片文字从PPT大纲"元素"字段读取，不从narration截取
□ 所有图片base64内联，禁止文件路径
□ GSAP timeline注册到 window.__timelines["s{id}"]
□ 每页暴露 window.__hf["s{id}"] = {duration, seek}
□ 每页右下角显示页码
□ 完成后再做一次browser预览检查
```

```
T0 ──→ T1 ──→ T3 ──→ TTS实测 ──→ T2 ───→ T5 ───→ T6 ───→ T7
选题   知识点   口播稿              PPT     配图     compositions 渲染+
研究   大纲     先行              大纲+    按image_  含图     配音
                                    分镜    slots.json         （T5先于T6）
```

### 【强制】T3必须在T2之前（口播先行）
- ✅ 必须：bianju先写完整口播稿，不限字数
- ✅ 必须：启明用edge-tts生成TTS，ffprobe实测时长
- ✅ 必须：meishu拿到口播稿+TTS实测时长后才开始设计PPT
- ❌ 禁止：meishu自己估算时长再让bianju填空

| 阶段 | 执行者 | 模型 | 执行方式 | 自主权 |
|------|--------|------|---------|--------|
| **T0** | xuan-ti-yan-jiu-yuan | deepseek-v4-pro | delegate_task | 定义选题范围、设计主类比 |
| **T1** | yanjiuyuan | deepseek-v4-pro | delegate_task | 组织知识结构 |
| **T3** | bianju | MiniMax-M2.7 | delegate_task | 口语化表达、例子选择 |
| **TTS** | **启明** | — | terminal(background) | **无自主权**，机械执行 |
| **T2** | meishu | MiniMax-M2.7 | delegate_task | 视觉设计、布局选择 |
| **T5** | chuangzuo / 启明 | MiniMax-M2.7 | terminal(background) | **无自主权**，按 image_slots.json 的 filename 字段生成到 images/ 目录 |
| **T6** | editor | qwen3.6-plus | delegate_task | 编码实现、布局优化 |
| **T7** | hyperframes-producer | deepseek-v4-flash | terminal(background) | **无自主权**，渲染+合并 |
| **T8** | zimu-agent | deepseek-v4-flash | 按需启用 | 字幕样式调整 |

---

## §1. 口播与TTS规范（T3 bianju + 启明）

### §1.1 目标字数
```
目标字数 = slide时长(秒) × 5.26
有效语速：--rate=-15% (≈1.15x) → 5.26字/秒
容差：±5%
```

### §1.2 TTS生成（启明执行）
- ✅ 必须：用 `python3 -m edge_tts --voice zh-CN-XiaoxiaoNeural -f 口播稿.txt --write-media output.mp3`
- ✅ 必须：用 `-f` 文件模式（不要用 `--text`，特殊字符会shell转义失败）
- ✅ 必须：ffprobe测量实际时长
- ✅ 必须：用 `--rate=-15%（服务端变速，音质优于 atempo；不可用时回退 atempo=1.15,volume=6dB）` 加速
- ✅ 必须：音频统一 `-ac 1 -ar 24000`（单声道+24000Hz）
- ❌ 禁止：用 `edge-tts` 命令（不在PATH中，要用 `python3 -m edge_tts`）

### §1.3 口播稿格式
- ✅ 纯文字稿，不加时间/页码标记（TTS实测后才能确定时长）
- ❌ 禁止用 `##` markdown标题（会被edge-tts读成"井号井号"）
- ❌ 禁止用 `**加粗**` 或 `` `代码` `` 标记（渗入narration后字幕出现符号）

---

## §2. PPT大纲规范（T2 meishu）

### §2.1 信息密度（强制）
| 页面类型 | 最少层数 | 必须包含 |
|---------|---------|---------|
| 封面 | 3层 | 标题80px + 副标题 + 进度装饰 |
| 核心概念页 | 4层 | badge + h2(54px) + 2-3个card(22px/18px) + 视觉区 + 进度 |
| 代码页 | 3层 | 标签 + 标题 + 代码块25-35行(#13131a左对齐) |
| 过渡页 | 3层 | 标题 + 副标题 + 装饰 |
| 总结页 | 4层 | badge + 标题 + 多card + CTA |

### §2.2 禁止的薄页面
- ❌ 只有1个point-card + 1张图
- ❌ 纯大号emoji占位
- ❌ 标题含"[动画]"但实际静态
- ❌ 一句话+全屏背景
- ❌ 相邻两页同一种布局

### §2.3 产出物
1. **PPT大纲.md** — 每页的布局类型、元素清单、卡片文字（来源：meishu设计）
2. **timeline.json** — 每页id/start/end/duration/narration_text，精确对齐TTS实测
3. **image_slots.json** — 每页的配图需求（page/slot/content/source/size/prompt）
   - source=real（现实图，T4处理）| source=ai（AI图，T5处理）| source=code（无图）

---

## §3. HyperFrames Composition规范（T6 editor）

### §3.1 【强制】图片必须base64内联
```python
# 在生成composition时：
import base64
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
img_html = f'<img src="data:image/png;base64,{b64}">'
```
- ❌ 禁止：`<img src="file:///path/to/image.png">` — Chrome不加载
- ❌ 禁止：`<img src="../../path/to/image.png">` — 相对路径解析错误
- ✅ 必须：所有图片一律base64

### §3.2 【强制】GSAP timeline注册
每个composition必须注册timeline：
```javascript
(function() {
  var tl = gsap.timeline({paused: true});
  tl.from(".el1", {opacity: 0, x: -20, duration: 0.4});
  tl.from(".el2", {opacity: 0, y: 20, duration: 0.5}, "-=0.2");
  // ... 各元素依次渐入

  window.__timelines = window.__timelines || {};
  window.__timelines["s{id}"] = tl;     // ★ 必须注册
  window.__hf = window.__hf || {};
  window.__hf["s{id}"] = {              // ★ 必须暴露API
    duration: {dur},
    seek: function(t) {
      var tl = window.__timelines && window.__timelines["s{id}"];
      if (tl) tl.seek(t);
    }
  };
})();
```
- ✅ 必须：`paused: true`
- ✅ 必须：注册到 `window.__timelines`
- ✅ 必须：暴露 `window.__hf`（HyperFrames渲染器要求）
- ❌ 禁止：用 `gsap.to()` 替代 CSS初始状态（要用 `gsap.from()`）

### §3.3 【强制】每页不同布局
从以下10种轮换，相邻页不能重复：
- **hero** — 全屏背景+标题居中（封面/过渡页）
- **standard concept** — 左文右图
- **flipped concept** — 左图右文
- **comparison** — 双栏对比
- **data-chart** — 数据图表
- **flowchart** — 流程图/SVG连线
- **quote-definition** — 居中引用
- **card-grid** — 多卡片网格
- **timeline** — 时间轴
- **code-block** — 深色代码区(#13131a,左对齐,无图)

### §3.4 【强制】卡片文字来源
- ✅ 必须：从PPT大纲.md的"元素"字段读取完整文字
- ❌ 禁止：从narration_text硬切（中文不能字符数硬切）
- ❌ 禁止：用 `p[:18]` 这种硬截断

### §3.5 字体规范
- ✅ 使用 `font-family: sans-serif`（不要用具体字体名）
- ❌ 禁止：`PingFang SC`、`Microsoft YaHei`、`Noto Sans SC`（HyperFrames渲染器没有这些字体）
- ❌ 禁止：外部字体CDN链接（渲染时可能无法加载）

### §3.6 主index.html格式
```html
<div id="root" data-composition-id="main" data-start="0" data-duration="{总时长}" data-width="1920" data-height="1080">
  <div data-composition-id="s1" data-composition-src="compositions/scene_1.html" data-start="0.00" data-duration="10.00" data-width="1920" data-height="1080"></div>
  <!-- ...28页 -->
</div>
<script>window.__timelines=window.__timelines||{};window.__timelines["main"]=gsap.timeline({paused:true});</script>
<script>window.__hf=window.__hf||{};window.__hf["main"]={duration:{总时长},seek:function(t){var tl=window.__timelines&&window.__timelines["main"];if(tl)tl.seek(t);}};</script>
```

---


## §5. 管线自检与心跳规范（强制）
- pipeline_state.json 的每个 in_progress 步骤必须有 heartbeat_ts
- 停滞定义：in_progress 超过 15 分钟无 heartbeat_ts 更新
- 遇到停滞步骤，先 check_output 确认状态，再 repair
- 手动更新心跳：
- 手动校验：

## §4. 渲染规范（T7 hyperframes-producer）

### §4.1 命令
```bash
cd {项目}/04_PPT && hyperframes render . --fps 15 -o ../05_视频成品/final.mp4
```
- ✅ --fps 15（30fps会超时）

### §4.2 音频合并
```bash
ffmpeg -i final.mp4 -i 配音_加速.mp3 -c:v copy -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 -shortest final_有声.mp4
```

### §4.3 渲染失败排查
| 错误 | 原因 | 修复 |
|------|------|------|
| `window.__hf not ready` | composition缺少window.__hf | 加入§3.2的__hf代码 |
| font_family_without_font_face | 用了PingFang等字体 | 改用sans-serif |
| Docker not available | Mac没装Docker | 不加--docker参数 |

---

## §5. 各Agent强制Checklist

### T6 editor checklist（delegate_task context中必须逐条写入）
```
□ 【强制】优先使用 HyperFrames Block Catalog 中的 block
   参考: AGENTS.md §3 布局列表 / ~/.hermes/skills/hyperframes-v2-pipeline/references/block-customization-rules.md
□ 【强制】每页根据内容类型选择对应布局/block
   感性/类比 → concept / flipped（配T5 AI图）
   理性/数据 → data-chart（block自带柱状图/折线）
   理性/流程 → flowchart（block自带箭头动画）
   理性/代码 → code-block（#13131a深色背景）
   理性/对比 → comparison（双栏入场动画）
   感性/引用 → quote（深色背景居中）
   列举/总结 → card-grid / timeline-h
   封面/过渡 → hero
   无匹配block → 用 scripts/generate_composition.py 兜底
□ 【强制】用block时只改数据标签和文字，不改CSS class/position/flex/grid/GSAP结构
□ 【强制】所有图片base64内联，禁止任何文件路径
□ 【强制】每页GSAP timeline注册到 window.__timelines["s{id}"]
□ 【强制】每页暴露 window.__hf["s{id}"] = {duration, seek}
□ 【强制】每页布局不同（相邻页不能重复）
□ 【强制】卡片文字来自PPT大纲"元素"字段，不从narration截取
□ 【强制】中文文字完整显示，不硬切
□ 【强制】字体用 sans-serif，不用具体字体名
□ 信息密度≥PPT大纲标注的层数
□ 封面80px深色渐变背景，内容页白底标题54px
□ 每页右下角显示页码 "{id}/28"
□ 完成browser预览检查（内容不溢出）
```

## §6. 历史陷阱（每次开新视频前必读）

### 6.1 T4不是独立agent
❌ 错误：创建soucang profile + SOUL.md + config.yaml（多此一举）
✅ 正确：T4 = 启明直管的Python脚本，terminal(background)执行
**原因：** T4只需要读取+搜索+下载，不需要任何思考能力。

### 6.2 不能跳过agent
❌ 错误：启明自己写composition生成器（布局单一、文字硬切、路径错）
✅ 正确：T6委托给editor agent（qwen3.6-plus），它会读PPT大纲选布局
**原因：** 跳过agent = 放弃独立思考 + 没shenheyuan审计

### 6.3 图片必须base64
❌ 错误：`../../03_图片素材/ai/P01.png`（从文件系统看路径对，但渲染裂）
✅ 正确：读文件→base64.b64encode→`data:image/png;base64,xxx`
**原因：** M5 Pro Mac的Chrome headless不可靠加载本地文件

### 6.4 GSAP必须注册timeline
❌ 错误：`<script>gsap.from(...)</script>`（元素瞬间出现，不动）
✅ 正确：`window.__timelines["s{id}"] = gsap.timeline({paused: true})`
**原因：** HyperFrames通过window.__timelines控制播放

### 6.5 wuyinkeji API调用
- 提交：key放body `{"key":"xxx","prompt":"...","size":"16:9"}`
- 轮询：key放query `?key=xxx&id=TASK_ID`（两个位置不同！）
- status=3：内容审核不通过，换prompt重试

### 6.6 字幕按需启用
- 字幕默认不生成，主人明确需要时才做
- 生成方式：ASS格式，分页锚定法，MKV封装

---

## §8. 开工检查清单（每次新选题必须执行）

### §8.1 启动前检查
- [ ] `hermes profile list | wc -l` — 确认8个profile都存在（yanjiuyuan, bianju, meishu, chuangzuo, editor, shenheyuan, xuan-ti-yan-jiu-yuan, zimu-agent）
- [ ] 已在Kanban创建完整任务链（没有Kanban=不存在）
- [ ] 配图API可用性检查（wuyinkeji key有效？ComfyUI在运行？）
- [ ] 确定降级方案：API不可用时走SVG占位
- [ ] 加载本AGENTS.md，确认最新版本
- [ ] 与主人确认审核节奏：全自动 / 分阶段审核
- [ ] 确认TTS语速参数（当前：--rate=-15%, volume=6dB）

### §8.2 渲染前检查
- [ ] compositions的渲染规则全遵守了吗？（§3）
- [ ] 所有图片是base64内联吗？
- [ ] 每个composition注册了window.__timelines + window.__hf吗？
- [ ] 每页布局不同吗？（相邻页不能重复）
- [ ] 卡片文字来自PPT大纲"元素"字段吗？

### §8.3 交付前检查
- [ ] 音画时长对齐？（ffprobe验证≤1%差异）
- [ ] 有口播的页时长足够吗？
- [ ] 静音页≤8秒吗？（旧管线教训）
- [ ] v5成品在主人面前打开验证过吗？

| 参数 | 值 | 说明 |
|------|----|------|
| 语速 | --rate=-15% + volume=6dB | 有效语速5.26字/秒 |
| 目标字数 | 时长×5.26 | ±5%容差 |
| 帧率 | 15fps | 30fps超时 |
| 画面 | 1920×1080 | |
| 封面 | 深色渐变#0a0a1a~#1a0a2e | 标题80px白字 |
| 内容页白底 | #ffffff / #f8f6ff | 标题54px #222, 卡片22px #333, 正文18px #555 |
| TTS | edge-tts zh-CN-XiaoxiaoNeural | python3 -m edge_tts，-f文件模式 |
| 音频格式 | 24000Hz mono | -ac 1 -ar 24000 |
| 配图API | wuyinkeji 异步API | 提交body→轮询query，~55秒/张 |
| 像素要求 | ≥1280×720 | ffprobe验证 |

---

## §9. 工具链（scripts/ 目录）

| 脚本 | 用途 | 阶段 |
|------|------|------|
| `pipeline.py` | 状态编排器：start/step/status/repair/skip | 全流程 |
| `calc_timeline_offsets.py` | 时长列表 → 自动 data-start（支持 --verify） | TTS 后 |
| `tts_to_durations.py` | 口播稿 → TTS 生成 → 每段实测时长 → timeline.json | TTS 阶段 |
| `generate_composition.py` | 10 种布局模板 → composition HTML | T6 |
| `images_to_base64.py` | 图片目录 → base64 映射 JSON | T4/T5 后 |
| `harness.py` | 三段式门禁：phase1/2/3 | 渲染前/交付前 |
| `render_perf_log.py` | 记录渲染性能指标 | T7 后 |

### 典型使用顺序
```bash
# 创建项目
bash go.sh start '主题' 2

# TTS 全自动
python3 scripts/tts_to_durations.py --input episodes/第2期/配音稿_分段.txt --generate

# 自动 data-start
python3 scripts/calc_timeline_offsets.py --list "6,8.5,7.5" --verify index.html

# 渲染前门禁
python3 scripts/harness.py 第2期_主题 2

# 交付前门禁
python3 scripts/harness.py 第2期_主题 3
```
