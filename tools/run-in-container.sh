#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ACTIVE_CHECKLISTS=(python cpp nodejs julia r go rust)
PLANNED_CHECKLISTS=()

usage() {
  cat <<'EOF'
Usage:
  ./tools/run-in-container.sh list
  ./tools/run-in-container.sh checklist [language]
  ./tools/run-in-container.sh all-checklists
  ./tools/run-in-container.sh <language>

Active checklist:
  python cpp nodejs julia r go rust
EOF
}

need_cmd() {
  local cmd="$1"
  local hint="${2:-Install it in the ohdev container, then run again.}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing runtime: $cmd. $hint" >&2
    exit 127
  fi
}

run_python_checklist() {
  need_cmd python3
  python3 tools/python_checklist_status.py python
}

run_cpp_checklist() {
  need_cmd python3
  python3 tools/cpp_checklist_status.py
}

run_nodejs_checklist() {
  need_cmd python3
  python3 tools/nodejs_checklist_status.py
}

run_julia_checklist() {
  need_cmd python3
  python3 tools/julia_checklist_status.py
}

run_r_checklist() {
  need_cmd python3
  python3 tools/r_checklist_status.py
}

run_go_checklist() {
  need_cmd python3
  python3 tools/go_checklist_status.py
}

run_rust_checklist() {
  need_cmd python3
  python3 tools/rust_checklist_status.py
}

run_one() {
  local lang="$1"
  case "$lang" in
    py|python) run_python_checklist ;;
    c++|cpp) run_cpp_checklist ;;
    js|javascript|node|nodejs) run_nodejs_checklist ;;
    julia|jl) run_julia_checklist ;;
    r|R) run_r_checklist ;;
    go|golang) run_go_checklist ;;
    rust|rs) run_rust_checklist ;;
    *) echo "Unknown language: $lang" >&2; usage; exit 2 ;;
  esac
}

main() {
  local target="${1:-}"
  case "$target" in
    ""|-h|--help|help) usage ;;
    list)
      printf 'active checklists: %s\n' "${ACTIVE_CHECKLISTS[*]}"
      ;;
    checklist)
      shift || true
      case "${1:-all}" in
        ""|all|all-checklists)
          for lang in "${ACTIVE_CHECKLISTS[@]}"; do
            printf '\n==> %s\n' "$lang"
            run_one "$lang"
          done
          ;;
        py|python) run_python_checklist ;;
        c++|cpp) run_cpp_checklist ;;
        js|javascript|node|nodejs) run_nodejs_checklist ;;
        julia|jl) run_julia_checklist ;;
        r|R) run_r_checklist ;;
        go|golang) run_go_checklist ;;
        rust|rs) run_rust_checklist ;;
        *) echo "Unknown checklist language: $1" >&2; usage; exit 2 ;;
      esac
      ;;
    all|all-checklists)
      for lang in "${ACTIVE_CHECKLISTS[@]}"; do
        printf '\n==> %s\n' "$lang"
        run_one "$lang"
      done
      ;;
    *)
      run_one "$target"
      ;;
  esac
}

main "$@"
