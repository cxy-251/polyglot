#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMMAND=${1:-status}

require_language_root() {
  local language=$1
  if [[ ! -d "$ROOT/languages/$language" ]]; then
    echo "languages/$language does not exist yet; complete its foundation task first." >&2
    exit 2
  fi
}

case "$COMMAND" in
  check|status)
    exec python3 "$ROOT/tools/project.py" "$COMMAND"
    ;;
  next)
    shift || true
    exec python3 "$ROOT/tools/project.py" next "$@"
    ;;
  task)
    shift || true
    exec python3 "$ROOT/tools/project.py" task "$@"
    ;;
  python)
    require_language_root python
    exec python3 -m pytest -q "$ROOT/languages/python"
    ;;
  cpp)
    require_language_root cpp
    build_dir="${TMPDIR:-/tmp}/polyglot-cpp-build"
    cmake -S "$ROOT/languages/cpp" -B "$build_dir"
    cmake --build "$build_dir"
    exec ctest --test-dir "$build_dir" --output-on-failure
    ;;
  nodejs)
    require_language_root nodejs
    cd "$ROOT/languages/nodejs"
    exec node --test
    ;;
  julia)
    require_language_root julia
    cd "$ROOT/languages/julia"
    exec julia --project=. runtests.jl
    ;;
  r)
    require_language_root r
    exec Rscript "$ROOT/languages/r/test_base.R"
    ;;
  go)
    require_language_root go
    cd "$ROOT/languages/go"
    exec go test ./...
    ;;
  rust)
    require_language_root rust
    exec cargo test --manifest-path "$ROOT/languages/rust/Cargo.toml"
    ;;
  all)
    for language in python cpp nodejs julia r go rust; do
      "$0" "$language"
    done
    ;;
  *)
    echo "usage: $0 {check|status|next [language]|task <id>|python|cpp|nodejs|julia|r|go|rust|all}" >&2
    exit 2
    ;;
esac
