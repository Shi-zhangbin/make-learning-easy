# Make Learning Easy 🚀

> AI 视频全自动生产线 — 专注技术教程
> 从一句话到带字幕的成品视频

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入你的 key

# 一句话做视频
bash go.sh create "用通俗易懂的方式讲Transformer"
```

## 管线流程

T0(选题) → T1(大纲) → T3(口播稿) → T4(配音+字幕) → T2(分镜) → T5(配图) → T6(Composition) → T7(渲染)

> 为什么口播(T2)在分镜(T4)之前？先写口播稿 → 生成真实 TTS 音频 → 实测每段时长 → 再按真实时长设计分镜。这样每页的停留时间与口播长度精确匹配，不会出现"画面翻过去了话还没说完"的问题。

| 步骤 | 说明 | 自动化 |
|------|------|--------|
| T0 | AI agent 写选题报告 | 自动委托 |
| T1 | AI agent 写知识点大纲 | 自动委托 |
| T3 | AI agent 写口播稿 | 自动委托 |
| T4 | edge-tts 配音 + whisper 字幕 | ✔ 全自动 |
| T2 | AI agent 设计分镜方案 | 自动委托 |
| T5 | 三级 fallback 配图生成 | ✔ 全自动 |
| T6 | 10 种布局模板渲染 composition | ✔ 全自动 + 门禁 |
| T7 | HyperFrames 渲染 + 音视频合成 | ✔ 全自动 |

## 致谢 / Credits

本项目在设计和实现过程中参考了以下开源项目：

| 项目 | 作者 | 说明 |
|------|------|------|
| [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | [harry0703](https://github.com/harry0703) | 字幕生成与图片搜索方案的设计参考 |
| [awesome-design-md](https://github.com/awesome-design-md) | 社区 | 品牌设计系统的分析文档 |
| [HyperFrames](https://hyperframes.heygen.com) | HeyGen | HTML 视频渲染引擎 |
| [edge-tts](https://github.com/rany2/edge-tts) | rany2 | 微软 Edge TTS 封装 |
| [whisper.cpp](https://github.com/ggerganov/whisper.cpp) | ggerganov | 本地语音识别引擎 |

内置设计风格的设计 tokens 来源于 [awesome-design-md](https://github.com/awesome-design-md)。

## 许可

MIT License
