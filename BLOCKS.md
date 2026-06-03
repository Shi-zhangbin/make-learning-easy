# HyperFrames Block Catalog — 内容类型 → 布局映射

> 优先使用 block，只有没有匹配 block 时才用 `scripts/generate_composition.py`。

---

## 内容类型 → Block 映射

| 内容类型 | 适用的 Block | 配图来源 |
|---------|-------------|---------|
| 感性 / 概念类比 | concept-block / flipped-block | T5 AI 配图 (base64 内联) |
| 感性 / 场景描述 | hero-block / quote-block | T5 AI 配图 |
| 感性 / 开场白 | hero-block | 无 / 全屏渐变 |
| 理性 / 代码展示 | code-block | 无（深色背景代码区） |
| 理性 / 流程图 | flowchart / data-flowchart block | 无（SVG 箭头动画） |
| 理性 / 数据对比 | comparison block | 无（双栏布局） |
| 理性 / 数据图表 | data-chart block | 无（柱状图/折线图） |
| 理性 / 时间线 | timeline-h block | 无 |
| 理性 / 列举要点 | card-grid block | 无 / 图标 |
| 理性 / 引用定义 | quote-block | T5 AI 配图 |
| 结尾 | logo-outro block / hero-block | T5 AI 配图 |

---

## Block 使用规则

### 可改的

| 字段 | 说明 |
|------|------|
| `<title>` | composition 标题 |
| 标题/卡片文字 | 只替换文本内容 |
| 数据标签 | 图表 label、数值 |
| `data-composition-id` | 与 index.html 对齐 |
| `data-start` / `data-duration` | 从 timeline.json 取值 |
| 图片 URL | 替换为 base64 data URI |
| `window.__hf` | 添加 `__hf["s{id}"] = {duration, seek}` |

### 不可改的

| 字段 | 原因 |
|------|------|
| CSS class 名 | block 内部 GSAP 通过 class 控制动画 |
| position / flex / grid 代码 | block 布局是设计好的 |
| GSAP timeline 结构 | block 有自己的注册逻辑 |
| `window.__timelines` 注册方式 | 必须保持 block 原有的 |
| 外部 CDN / 字体引用 | 改了可能渲染失败 |
| `<style>` 中的选择器 | 可能破坏 block 动画 |

### 标准修改流程

```bash
# 1. 复制 block 模板到 compositions/
cp /path/to/block/compositions/data-chart.html episodes/第N期/compositions/scene_8.html

# 2. 只替换文本内容和数据标签
sed -i '' 's/原标题/新标题/' scene_8.html

# 3. 改外框 timing
sed -i '' 's/data-duration="[^"]*"/data-duration="10.00"/' scene_8.html

# 4. 加 __hf（在 </script> 前插入）
# 插入: window.__hf["s8"] = {duration:10, seek:function(t){...}}

# 5. ✅ 不改: CSS class, position, flex, grid, GSAP 结构
```

---

## 没有匹配 Block 时的兜底

用 `scripts/generate_composition.py`：

```bash
python3 scripts/generate_composition.py \
  --design-system designs/awesome-design-md/design-md/{style}/DESIGN.md \
  --layout {hero|concept|flipped|comparison|code-block|card-grid|flowchart|quote|timeline-h|data-chart} \
  --sid s1 --duration 10 --title "标题" \
  -o compositions/scene_1.html
```

兜底的布局颜色和字体从 DESIGN.md 自动读取，但不含 block 的定制 GSAP 动画。
