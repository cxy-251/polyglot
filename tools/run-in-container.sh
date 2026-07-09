#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ACTIVE_CHECKLISTS=(python)
PLANNED_CHECKLISTS=(cpp nodejs julia r go rust)

usage() {
  cat <<'EOF'
Usage:
  ./tools/run-in-container.sh list
  ./tools/run-in-container.sh checklist [language]
  ./tools/run-in-container.sh all-checklists
  ./tools/run-in-container.sh <language>

Active checklist:
  python

Planned checklist placeholders:
  cpp nodejs julia r go rust
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

run_checklist() {
  need_cmd python3
  shift || true
  python3 tools/python_checklist_status.py "$@"
}

run_python_checklist() {
  need_cmd python3
  python3 tools/python_checklist_status.py python
}

planned() {
  local lang="$1"
  echo "$lang is listed in catalog.json, but its checklist is still a placeholder." >&2
  exit 127
}

run_one() {
  local lang="$1"
  case "$lang" in
    py|python) run_python_checklist ;;
    c++|cpp) planned cpp ;;
    js|javascript|node|nodejs) planned nodejs ;;
    julia|jl) planned julia ;;
    r|R) planned r ;;
    go|golang) planned go ;;
    rust|rs) planned rust ;;
    *) echo "Unknown language: $lang" >&2; usage; exit 2 ;;
  esac
}

main() {
  local target="${1:-}"
  case "$target" in
    ""|-h|--help|help) usage ;;
    list)
      printf 'active checklists: %s\n' "${ACTIVE_CHECKLISTS[*]}"
      printf 'planned checklist placeholders: %s\n' "${PLANNED_CHECKLISTS[*]}"
      ;;
    checklist)
      run_checklist "$@"
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
