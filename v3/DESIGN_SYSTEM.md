# v3 设计系统文档

## 架构分层

```
┌─────────────────────────────────────────────┐
│  设计预设 (designs/presets/*.yaml)           │  ← 可替换
│  颜色 / 字体 / 圆角 / 阴影                   │
├─────────────────────────────────────────────┤
│  组件CSS (templates/teaching_components.css) │  ← 稳定
│  .feature-card / .code-window / .step-card   │
├─────────────────────────────────────────────┤
│  布局模板 (templates/layouts/*.j2)          │  ← 最稳定
│  结构 + 间距系统，不包含视觉样式              │
├─────────────────────────────────────────────┤
│  PageSpec (pagespec.py)                     │  ← 数据层
│  结构化页面数据 → 模板渲染                   │
└─────────────────────────────────────────────┘
```

## 间距系统（所有布局统一）

| 间距 | 值 | 用途 |
|------|-----|------|
| badge_bottom | 12px | badge → title |
| title_bottom | 4px | title → subtitle |
| subtitle_bottom | 10px | subtitle → 第一个卡片/内容区域 |
| section_gap | 18px | 卡片之间、组件之间 |
| content_margin | 6px | 内容区域顶部 |
| image_margin | 14px | 图片区域顶部 |
| 页面内边距 | 48px top, 72px left/right | .sl container |

## 布局模式（7种）

### 1. Hero（封面）
- 左文右图（6:4）
- 标题 56px
- 图片区域 420px 高
- 适合：视频封面页

### 2. Concept（概念讲解）
- 左文右图（6:4）
- 标题 38px
- 卡片在左栏垂直居中
- 图片右侧全高
- 适合：核心概念讲解

### 3. Flipped（翻转布局）
- 左图右文（4:6）
- 和 Concept 对称
- 适合：示意图在左、文字说明在右

### 4. Comparison（对比布局）
- 文字对比栏在上方
- 大图 fill 剩余空间
- 对比栏用分隔线隔开
- 适合：概念对比、方案对比

### 5. Code Block（代码展示）
- 左代码窗口（60%）+ 右注解（40%）
- 代码在深色窗口中显示，格式保持原样
- 没有配图，代码是手写真实代码
- 适合：代码示例、算法实现

### 6. Flowchart（流程图）
- 步骤卡片横向排列，箭头连接
- 大图 fill 剩余空间
- 适合：流程说明、步骤拆解

### 7. Card Grid（卡片网格）
- 2×2 网格
- 大图 fill 剩余空间
- 适合：要点归纳、分类对比

## 组件分类

### 结构组件（在 templates 中直接使用）
```
.sl              — 页面内容容器（flex column, padding 48px 72px）
.flex-row        — 水平弹性布局（gap: 18px）
.flex-col        — 垂直弹性布局
.flex-1 / .flex-08 / .flex-14  — flex 比例
.card-grid-2x2   — 2×2 网格（gap: 20px）
```

### 视觉组件（通过 teaching_components.css 定义）
```
.badge-section          — 章节标签（蓝底白字圆角）
.feature-card           — 内容卡片（白底灰边框）
.code-window            — 代码窗口（深色背景 + 红黄绿圆点标题栏）
.compare-col            — 对比列（浅灰底色）
.step-card              — 流程步骤卡片（白底灰边框）
.step-arrow             — 箭头（蓝色）
.image-rail            — 图片容器（浅灰底 + 圆角）
.page-number            — 页码（固定在底部右下角）
```

### 排版组件（typography）
```
.page-title    — 页面大标题（42px/38px/34px 根据布局调整）
.page-subtitle — 页面副标题（17-18px，灰色）
h3（卡片内）   — 卡片标题（17px）
p（卡片内）    — 卡片正文（15px，#3d3d4a）
```

## 数据流

```
timeline.json（每页时长+标题）
    ↓
image_slots.json（配图规划）
    ↓
build_all_pages() → list[PageSpec]
    ↓
PageSpec 包含: layout / badge / title / sections[Section{cards, code, comparison}] / image_slot
    ↓
Jinja2 模板渲染: {{ page_spec.layout }}.j2 + teaching_components.css
    ↓
composition HTML（GSAP + __hf + standalone 已内嵌）
```

## 关键约束

### 每页最少层数
```
hero=5, concept=6, comparison=6, code_block=5,
flowchart=5, card_grid=5, outro=3, quote=4, section_divider=4
```

### 表面节奏
- 默认全在 cream 色系：cream → cream_soft → cream_card → cream_soft → ...
- 深色背景只用于代码 window（代码页渲染时使用），不用于页面底色

### 图片规则
- code_block 页面不使用 AI 配图，显示真实代码
- 其他页面用 wuyinkeji 优先，Pexels/Pixabay 降级，SVG 兜底
- prompt 格式：详细中文描述（白底 + 科技蓝主色 + 手绘风格 + 精确布局说明）
- 图片填满 flex:1 剩余区域，不固定高度

## 如何新增风格

1. 在 `designs/presets/` 下新建 YAML（参考 claude.yaml 结构）
2. 在 `teaching_components.css` 中新增/覆盖对应 token 的颜色值
3. 不需要改布局模板

## 如何新增布局

1. 在 `templates/layouts/` 下新建 `.j2` 文件
2. 在 `pagespec.py` 的 `LAYOUTS` 列表和 `MIN_LAYERS` 字典中添加
3. 在 `BADGE_PREFIXES` 和 `build_pagespec()` 中添加布局逻辑
4. 在 `layout_rotation` 中使用新布局名
