#!/bin/bash
# Make Learning Easy Pipeline v3
# Usage:
#   bash go.sh quick --name "第N期_主题" --preset dark-teal
#   bash go.sh run --episode "第N期_主题" --step T6
#   bash go.sh create --name "第N期_主题" --topic "..." --auto

set -e
cd "$(dirname "$0")"

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in
  quick)
    NAME=""; PRESET="claude"
    while [ $# -gt 0 ]; do
      case "$1" in --name) NAME="$2"; shift;; --preset) PRESET="$2"; shift;; *) shift;; esac
      shift
    done
    if [ -z "$NAME" ]; then echo "Usage: bash go.sh quick --name \"第N期_主题\" [--preset dark-teal]"; exit 1; fi
    mkdir -p "episodes/$NAME"/{compositions,audio,images,成品}
    cat > "episodes/$NAME/pipeline_state.json" << EOF
{
  "episode": "$NAME",
  "topic": "$NAME",
  "current_step": "T6",
  "steps": {"T0":{"status":"skipped"},"T1":{"status":"skipped"},"T2":{"status":"done"},"T3":{"status":"skipped"},"T4":{"status":"done"},"T5":{"status":"skipped"}},
  "design_style": "$PRESET",
  "created_at": "$(date +%Y-%m-%d)"
}
EOF
    echo "📁 episodes/$NAME 已创建，design_style: $PRESET"
    echo "   → 写 timeline.json"
    echo "   → bash go.sh run --episode \"$NAME\" --step T6"
    ;;
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

  quick   快速创建新期目（跳过内容生成，直接到 T6）
          bash go.sh quick --name "第N期_主题" --preset dark-teal
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
