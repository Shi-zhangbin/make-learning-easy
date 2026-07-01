#!/bin/bash
# Make Learning Easy Pipeline
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
    python3 -m core.engine run "$@"
    ;;
  create)
    python3 -m core.engine create "$@"
    ;;
  status)
    python3 -m core.engine status "$@"
    ;;
  list)
    python3 -m core.engine list
    ;;
  designs)
    python3 -m core.engine designs
    ;;
  tones)
    python3 -m core.engine tones
    ;;
  layouts)
    python3 -m core.engine layouts
    ;;
  help)
    cat << USAGE
Make Learning Easy Pipeline

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
  tones   列出可用话风预设
  status  查看期目状态
          bash go.sh status --episode "2026-06-26_主题_[Agent]"
  init    初始化新期目（指定 --style 和 --tone）
          bash go.sh init "2026-06-26_主题_[Agent]" --topic "..." --style bilibili --tone talk-show
USAGE
    ;;
  *)
    echo "Unknown command: $CMD"
    bash go.sh help
    ;;
esac
