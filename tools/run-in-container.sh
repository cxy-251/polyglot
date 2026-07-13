#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./tools/run-in-container.sh doctor
  ./tools/run-in-container.sh python [pytest arguments...]

Host entry point:
  ./tools/run.sh <command>
EOF
}

need_cmd() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ohdev 中缺少运行时或工具: $command_name" >&2
    exit 127
  fi
}

doctor() {
  need_cmd python3
  printf 'workspace: %s\n' "$ROOT"
  printf 'python: '
  python3 --version
  printf 'pytest: '
  python3 -m pytest --version
}

run_python() {
  need_cmd python3
  if [[ $# -eq 0 ]]; then
    python3 -m pytest languages/python
  else
    python3 -m pytest "$@"
  fi
}

main() {
  local command_name="${1:-}"
  case "$command_name" in
    doctor)
      doctor
      ;;
    python|py)
      shift
      run_python "$@"
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      echo "未知命令: $command_name" >&2
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
