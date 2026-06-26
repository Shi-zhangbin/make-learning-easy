#!/bin/bash
# Make Learning Easy Pipeline v3
# Usage:
#   bash go.sh run --episode "2026-06-26_主题_[Agent]" --step T6
#   bash go.sh create --name "2026-06-26_主题_[Agent]" --topic "..." --auto
#
# Naming convention: YYYY-MM-DD_主题_[Agent]
#   Agent: Codex, Claude-Code, Hermes
#   Example: 2026-06-26_云服务的前世今生_[Codex]
#   Legacy: 第N期_主题 (supported for backward compat)

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
  help)
    cat << USAGE
Make Learning Easy Pipeline v3

命名规范: YYYY-MM-DD_主题_[Agent]
  Agent: Codex, Claude-Code, Hermes
  示例: 2026-06-26_云服务的前世今生_[Codex]
  旧格式向后兼容: 第N期_主题

  run     运行管线步骤
          bash go.sh run --episode "2026-06-26_主题_[Agent]" --step T6
  create  完整创建（含内容生成）
          bash go.sh create --name "2026-06-26_主题_[Agent]" --topic "..."
  list    列出所有期目
  designs 列出可用设计预设
  status  查看期目状态
          bash go.sh status --episode "2026-06-26_主题_[Agent]"
USAGE
    ;;
  *)
    echo "Unknown command: $CMD"
    bash go.sh help
    ;;
esac
