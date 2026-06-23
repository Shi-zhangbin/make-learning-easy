#!/usr/bin/env bash
# ascend-pipeline v3 — 一句话做视频
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"

case "${1:-help}" in
  create|new|做视频|新建)
    shift
    # Usage: bash go.sh create "主题" [项目名] [风格]
    TOPIC="$1"
    EP="${2:-}"
    STYLE="${3:-claude}"
    
    if [ -z "$TOPIC" ]; then
      echo "用法: bash go.sh create \"你的主题描述\" [项目名] [风格]"
      echo "示例: bash go.sh create \"用通俗易懂的方式讲明白Transformer是什么，适合编程新手\""
      echo "示例: bash go.sh create \"RNN循环神经网络\" 第6期_RNN claude"
      exit 1
    fi
    
    # Auto-generate project name if not provided
    if [ -z "$EP" ]; then
      EP_SHORT=$(echo "$TOPIC" | sed 's/[^a-zA-Z0-9\u4e00-\u9fff]//g' | head -c 20)
      EP="第$(ls "$BASE/episodes" 2>/dev/null | grep -c '^第' | awk '{print $1+1}')期_${EP_SHORT}"
    fi
    
    cd "$BASE" && PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine create "$EP" --topic "$TOPIC" --style "$STYLE"
    ;;
    
  status|进度)
    cd "$BASE" && PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine status --episode "${2:-}" ;;
    
  run|继续)
    shift
    cd "$BASE" && PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine run --episode "$@" ;;
    
  list|列表)
    cd "$BASE" && PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine list ;;
    
  designs|风格)
    cd "$BASE" && PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine designs ;;
    
  help|--help|-h|"")
    echo "━" Make Learning Easy "━" AI 视频生产线 v3
    echo ""
    echo "一句话做视频:"
    echo "  bash go.sh create \"你的主题\""
    echo ""
    echo "示例:"
    echo "  bash go.sh create \"用通俗易懂的方式讲明白Transformer是什么\""
    echo "  bash go.sh create \"RNN循环神经网络\" 第6期_RNN claude"
    echo ""
    echo "其他命令:"
    echo "  bash go.sh status    查看项目进度"
    echo "  bash go.sh run       手动推进管线"
    echo "  bash go.sh list      列出所有项目"
    echo "  bash go.sh designs   查看可选风格"
    ;;
    
  *)
    cd "$BASE" && PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine "$@" ;;
esac
