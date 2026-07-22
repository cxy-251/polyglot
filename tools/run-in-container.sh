#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./tools/run-in-container.sh doctor
  ./tools/run-in-container.sh python [pytest arguments...]
  ./tools/run-in-container.sh cpp [ctest arguments...]
  ./tools/run-in-container.sh nodejs [node --test arguments or test files...]

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
  need_cmd g++
  need_cmd cmake
  need_cmd ctest
  need_cmd node
  need_cmd npm
  need_cmd julia
  need_cmd R
  need_cmd Rscript
  need_cmd go
  need_cmd gofmt
  need_cmd rustc
  need_cmd cargo
  need_cmd rustfmt
  printf 'workspace: %s\n' "$ROOT"
  printf 'python: '
  python3 --version
  printf 'pytest: '
  python3 -m pytest --version
  printf 'c++: '
  g++ --version | sed -n '1p'
  printf 'cmake: '
  cmake --version | sed -n '1p'
  printf 'ctest: '
  ctest --version | sed -n '1p'
  printf 'node: '
  node --version
  printf 'npm: '
  npm --version
  printf 'julia: '
  julia --startup-file=no --history-file=no --version
  printf 'R: '
  R --version | sed -n '1p'
  printf 'go: '
  go version
  printf 'rustc: '
  rustc --version
  printf 'cargo: '
  cargo --version
  printf 'rustfmt: '
  rustfmt --version
}

run_python() {
  need_cmd python3
  if [[ $# -eq 0 ]]; then
    python3 -m pytest languages/python
  else
    python3 -m pytest "$@"
  fi
}

run_cpp() {
  need_cmd g++
  need_cmd cmake
  need_cmd ctest

  local build_dir="${POLYGLOT_CPP_BUILD_DIR:-/tmp/polyglot-cpp-build}"
  local gtest_source="${POLYGLOT_GTEST_SOURCE:-/home/openharmony/third_party/googletest}"

  if [[ ! -f "$gtest_source/CMakeLists.txt" ]]; then
    echo "ohdev 中缺少锁定的 GoogleTest 源码: $gtest_source" >&2
    echo "可以通过 POLYGLOT_GTEST_SOURCE 指向兼容的 GoogleTest 1.16.0 源码。" >&2
    exit 127
  fi

  cmake \
    -S languages/cpp \
    -B "$build_dir" \
    -DCMAKE_BUILD_TYPE=Debug \
    -DPOLYGLOT_GTEST_SOURCE="$gtest_source"
  cmake --build "$build_dir" --parallel "${POLYGLOT_BUILD_JOBS:-4}"
  ctest \
    --test-dir "$build_dir" \
    --output-on-failure \
    --no-tests=error \
    "$@"
}

run_nodejs() {
  need_cmd node

  local expected_version="v24.18.0"
  local actual_version
  actual_version="$(node --version)"
  if [[ "$actual_version" != "$expected_version" ]]; then
    echo "Node.js 版本不匹配: 需要 $expected_version，实际 $actual_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-node-in-container.sh。" >&2
    exit 1
  fi

  local -a test_files=()
  if [[ $# -gt 0 && "$1" != -* ]]; then
    test_files=("$@")
    set --
  else
    mapfile -d '' test_files < <(
      find languages/nodejs \
        -type f \
        -name 'test_[0-9][0-9][0-9]_*.mjs' \
        -print0 | sort -z
    )
  fi

  if [[ ${#test_files[@]} -eq 0 ]]; then
    echo "languages/nodejs 中没有发现 test_NNN_*.mjs。" >&2
    exit 1
  fi

  NODE_OPTIONS="--unhandled-rejections=strict --trace-warnings" \
    node \
      --test \
      --test-concurrency=1 \
      "$@" \
      "${test_files[@]}"
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
    cpp|c++)
      shift
      run_cpp "$@"
      ;;
    nodejs|node|js)
      shift
      run_nodejs "$@"
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
