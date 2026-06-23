#!/usr/bin/env bash
# ascend-pipeline v3 shortcut
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$BASE:$PYTHONPATH" python3 -m v3.engine "$@"
