#!/bin/bash
# Make Learning Easy Pipeline v3
# Usage:
#   bash go.sh run --episode "第N期_主题" --step T6
#   bash go.sh create --name "第N期_主题" --topic "..." --auto

set -e
cd "$(dirname "$0")"

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in
  run)
    python3 -m v3.engine run "$@"
    ;;
  create)
    python3 -m v3.engine create "$@"
    ;;
  status)
    python3 -m v3.engine status "$@"
    ;;
  list)
    python3 -m v3.engine list
    ;;
  designs)
    python3 -m v3.engine designs
    ;;
  *)
    cat << USAGE
Make Learning Easy Pipeline v3

  run     运行管线步骤
          bash go.sh run --episode "第N期_主题" --step T6
  create  完整创建（含内容生成）
          bash go.sh create --name "第N期_主题" --topic "..."
  list    列出所有期目
  designs 列出可用设计预设
  status  查看期目状态
          bash go.sh status --episode "第N期_主题"
USAGE
    ;;
esac
