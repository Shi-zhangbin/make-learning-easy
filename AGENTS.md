 # Make Learning Easy — Agent 操作手册
 
 本文件供运行此项目的所有 AI Agent（Codex、Claude Code、Hermes 等）遵守。每次开始任务前必须读取。
 
 ## 项目定位
 
 这是一个 **AI 视频自动生产线**。输入一个主题，走完 T0→T7 管线，产出成品 MP4 视频。
 管线入口：`bash go.sh`，代码在 `v3/` 下，期目在 `episodes/` 下。
 
 ## 核心红线
 
 ### 1. 默认使用 bilibili 风格
 
 创建期目时，除非用户**明确指定**其他风格，一律使用 `--style bilibili`。
 
 ```bash
 python3 -m v3.engine init "第N期_主题" --topic "..." --style bilibili
 ```
 
 bilibili 预设特点：1920x1080，科技二次元配色，适合 B 站发布。
 
 ### 2. 严格执行视频时长要求
 
 用户要求"不少于 X 分钟"时，必须量化校验：
 
 - T2 口播稿写完后，用 `TTS_EFFECTIVE_CHARS_PER_SEC = 4.2`（配置在 `v3/config.py`）估算音频时长：
   `预估秒数 = 总有效字符数 / 4.2`
 - 预估时长必须**大于等于**用户要求的时长
 - 如果不够，回到 T2 加内容
 - 如果用户要求 10-15 分钟，目标写 **12 分钟以上**的稿子
 
 ### 3. 不允许产生占位符内容
 
 所有生成的内容文件（配音稿、PPT大纲、image_slots）必须为 **实际可用内容**。
 禁止输出 "卡片"、"图片"、"此处插入X" 等文字占位符。
 
 ### 4. 只处理指定的期目
 
 不要扫描 `episodes/` 目录做推测性工作。只创建/修改用户明确要求的期目。
 不要因为你看到 `episodes/` 下有其他期目就认为需要继续制作或修复它们。
 
 ### 5. 不允许跨期目污染
 
 所有产出文件必须在期目目录 `episodes/第N期_主题/` 下。
 不要往 `episodes/` 根目录写任何文件。
 
 ## 管线速查
 
 | 步骤 | 谁执行 | 产出 | 注意事项 |
 |------|--------|------|----------|
 | T0 | Agent | 选题研究报告.md | 核心知识点 5-8 个，教学类比 2-3 个 |
 | T1 | Agent | 知识点大纲.md | 4-7 个章节，一、二、三编号 |
 | T2 | Agent | 配音稿_分段.txt | 用 4.2 字/秒 校验时长，口语化 |
 | T3 | 自动 | narration.mp3/.srt/.ass | |
 | T4 | Agent | PPT大纲.md + image_slots.json | 每页配图需求标注 |
 | T5 | 自动 | 配图 | |
 | T6 | 自动 | index.html | 元素入场动画必须用 `duration` 非 `dur` |
 | T7 | 自动 | 成品/final.mp4 | 长视频（>5min）渲染较慢，单 worker 约需 30min |
 
 ## 已知风险
 
 - **T7 渲染慢**：GSAP 动画导致 `Runtime.callFunctionOn` 超时后降级单 worker。对 5 分钟以上的视频预留约 30 分钟渲染时间。
 - **字幕烧录**：因 ffmpeg filter 限制，含中文路径的 ASS 字幕无法烧入视频。字幕以独立 .srt/.ass 文件存储在 `audio/` 目录。
 - **图片裁剪**：容器内图片默认 `object-fit: cover`，如需完整显示请手动调整为 `contain`。
 
 ## Agent 步骤规范
 
 详见 `skills/ascend-video-pipeline.md` 和 `v3/engine.py`。
 
 Agent 步骤（T0/T1/T2/T4）完成后：
 1. 写入输出文件
 2. 删除 `.step_prompt.json`
 3. 重新执行同一步骤通过门禁
 
 通用规则：正文无 ##、**、``，口播稿无特殊字符。
