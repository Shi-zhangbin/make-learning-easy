#!/usr/bin/env bash
# go.sh — ascend-pipeline v3.1 统一入口
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"

help() {
  cat <<HELP
ascend-pipeline v3.1 — 一句话出片

用法:
  bash go.sh start <主题> [期号] [设计风格]
   例: bash go.sh start 'PyTorch推理入门' 2
       bash go.sh start '昇腾NPU' 3 mintlify

  bash go.sh step <项目名> [步骤]
   例: bash go.sh step 第2期_PyTorch推理入门
       bash go.sh step 第2期_PyTorch推理入门 TTS

  bash go.sh status <项目名>
  bash go.sh repair <项目名>
  bash go.sh skip <项目名> <步骤>

  bash go.sh verify <项目名> [步骤]
   例: bash go.sh verify 第3期_Qwen3.5-9B推理调优 T5

  bash go.sh heartbeat <项目名>
   更新当前运行步骤的心跳，防止超时检测

  bash go.sh check <项目名> [phase]
   例: bash go.sh check 第2期_PyTorch推理入门 2
       bash go.sh check 第2期_PyTorch推理入门 all

  bash go.sh list
   列出所有项目

工具链:
  scripts/pipeline.py              — 状态编排器 (v3.1)
  scripts/harness.py               — 三段式门禁
  scripts/tts_to_durations.py      — TTS 分段时长
  scripts/calc_timeline_offsets.py — auto data-start
  scripts/generate_composition.py  — 10种布局模板 (兜底)
  scripts/images_to_base64.py      — 图片→base64
  scripts/render_perf_log.py       — 渲染日志
HELP
  ls -1 "$BASE/episodes/" 2>/dev/null || echo "  (无)"
}

case "${1:-help}" in
  start)
    TOPIC="${2:? 缺少主题}"
    EP="${3:-1}"
    STYLE="${4:-mintlify}"
    EP_NAME="${EP}_${TOPIC}"
    # 新项目自动加编号
    if ! echo "$EP_NAME" | grep -q '^第'; then
      EP_NAME="第${EP_NAME}"
    fi
    python3 "$BASE/scripts/pipeline.py" start --topic "$TOPIC" --episode "$EP_NAME" --design "$STYLE"
    echo ""
    echo "  下一步: bash go.sh step '$EP_NAME'" ;;
  step)
    EP="${2:? 缺少项目名}"
    STEP="${3:-}"
    if [ -n "$STEP" ]; then
      python3 "$BASE/scripts/pipeline.py" step --episode "$EP" --step "$STEP"
    else
      python3 "$BASE/scripts/pipeline.py" step --episode "$EP"
    fi ;;
  status)   python3 "$BASE/scripts/pipeline.py" status --episode "${2:?}" ;;
  repair)   python3 "$BASE/scripts/pipeline.py" repair --episode "${2:?}" ;;
  skip)     python3 "$BASE/scripts/pipeline.py" skip --episode "${2:?}" --step "${3:?}" ;;
  verify)   python3 "$BASE/scripts/pipeline.py" verify --episode "${2:?}" --step "${3:-}" ;;
  heartbeat) python3 "$BASE/scripts/pipeline.py" heartbeat --episode "${2:?}" ;;
  check)
    EP="${2:?}"; PHASE="${3:-2}"
    if [ -f "$BASE/scripts/harness.py" ]; then
      python3 "$BASE/scripts/harness.py" "$EP" "$PHASE"
    else
      echo "⏳ harness 未部署 (Phase $PHASE 暂不可用)"
    fi ;;
  list)
    echo "项目:"; ls -1t "$BASE/episodes/" 2>/dev/null || echo "  (无)" ;;
  *) help ;;
esac
