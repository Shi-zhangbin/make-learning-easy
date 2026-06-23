# ascend-pipeline 管线规范

## 工作流
T0(选题) → T1(知识点) → T3(口播稿) → TTS实测 → [分镜对齐] → T2(PPT大纲) → T4+T5(素材) → T6(compositions) → T7(渲染) → T8(字幕)

## 设计风格
当前选定: Mintlify（白底+绿强调）
设计系统源: designs/awesome-design-md/design-md/mintlify/DESIGN.md

## 渲染前门禁
```bash
python3 scripts/harness.py episodes/第N期_xxxx phase2
```
通过后才能 render。

## 仓库结构
- designs/ — 设计系统库（awesome-design-md）
- specs/ — 管线规范
- scripts/ — 工具脚本（harness）
- episodes/ — 每期视频的内容目录
