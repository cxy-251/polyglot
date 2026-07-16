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
