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
  ./tools/run-in-container.sh go [go test arguments...]
  ./tools/run-in-container.sh concept NN_family/NN_topic
  ./tools/run-in-container.sh family NN_family
  ./tools/run-in-container.sh concepts
  ./tools/run-in-container.sh list-concepts
  ./tools/run-in-container.sh check

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
  printf 'go env: '
  go env GOOS GOARCH GOROOT GOWORK | paste -sd ' ' -
  printf 'gofmt: '
  command -v gofmt
  printf 'go vet: '
  go tool vet -help >/dev/null
  echo available
  printf 'rustc: '
  rustc --version
  printf 'cargo: '
  cargo --version
  printf 'rustfmt: '
  rustfmt --version
}

run_python() {
  need_cmd python3
  if [[ $# -eq 0 || "$1" == -* ]]; then
    python3 -m pytest languages/python "$@"
  else
    python3 -m pytest "$@"
  fi
}

run_cpp_layer() {
  local layer="$1"
  local build_dir="$2"
  local label="$3"
  shift 3

  need_cmd g++
  need_cmd cmake
  need_cmd ctest

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
    -DPOLYGLOT_TEST_LAYER="$layer" \
    -DPOLYGLOT_GTEST_SOURCE="$gtest_source"
  cmake --build "$build_dir" --parallel "${POLYGLOT_BUILD_JOBS:-4}"
  ctest \
    --test-dir "$build_dir" \
    --output-on-failure \
    --no-tests=error \
    -L "$label" \
    "$@"
}

run_cpp() {
  local build_dir="${POLYGLOT_CPP_BUILD_DIR:-/tmp/polyglot-cpp-build}"
  run_cpp_layer course "$build_dir" '^polyglot-language$' "$@"
}

check_nodejs_version() {
  need_cmd node

  local expected_version="v24.18.0"
  local actual_version
  actual_version="$(node --version)"
  if [[ "$actual_version" != "$expected_version" ]]; then
    echo "Node.js 版本不匹配: 需要 $expected_version，实际 $actual_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-node-in-container.sh。" >&2
    exit 1
  fi
}

run_nodejs() {
  check_nodejs_version
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
    echo "languages/nodejs/ 中没有发现 Node.js 课程测试。" >&2
    exit 1
  fi

  NODE_OPTIONS="--unhandled-rejections=strict --trace-warnings" \
    node \
      --test \
      --test-concurrency=1 \
      "$@" \
      "${test_files[@]}"
}

run_nodejs_files() {
  check_nodejs_version
  local -a test_files=("$@")

  NODE_OPTIONS="--unhandled-rejections=strict --trace-warnings" \
    node \
      --test \
      --test-concurrency=1 \
      "${test_files[@]}"
}

check_go_version() {
  need_cmd go
  need_cmd gofmt

  local expected_version="go1.26.5"
  local actual_version
  actual_version="$(go env GOVERSION)"
  if [[ "$actual_version" != "$expected_version" ]]; then
    echo "Go 版本不匹配: 需要 $expected_version，实际 $actual_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh go。" >&2
    exit 1
  fi
}

run_go() {
  check_go_version
  printf '\n== Go vertical course ==\n'
  (
    cd languages/go
    go test -count=1 "$@" ./...
    go vet ./...
  )
}

run_concept_go() {
  local concept_name="$1"
  if [[ -d "concepts/$concept_name/go" ]]; then
    check_go_version
    printf '\n== %s / Go ==\n' "$concept_name"
    (
      cd concepts
      go test -count=1 "./$concept_name/go"
    )
  fi
}

validate_concept_name() {
  local concept_name="$1"
  if [[ ! "$concept_name" =~ ^[0-9]{2}_[a-z0-9_]+/[0-9]{2}_[a-z0-9_]+$ ]]; then
    echo "概念名必须使用 NN_family/NN_topic 格式: $concept_name" >&2
    exit 2
  fi
  if [[ ! -d "concepts/$concept_name" ]]; then
    echo "概念目录不存在: concepts/$concept_name" >&2
    exit 2
  fi
}

run_concept_python() {
  local concept_name="$1"
  local -a test_files=()
  if [[ -d "concepts/$concept_name/python" ]]; then
    mapfile -d '' test_files < <(
      find "concepts/$concept_name/python" \
        -maxdepth 1 \
        -type f \
        -name 'test_[0-9][0-9]_*.py' \
        -print0 | sort -z
    )
    if [[ ${#test_files[@]} -eq 0 ]]; then
      echo "概念缺少 Python 测试: $concept_name" >&2
      exit 1
    fi
    need_cmd python3
    printf '\n== %s / Python ==\n' "$concept_name"
    python3 -m pytest --import-mode=importlib "${test_files[@]}"
  fi
}

run_concept_cpp() {
  local concept_name="$1"
  if [[ -d "concepts/$concept_name/cpp" ]]; then
    printf '\n== %s / C++ ==\n' "$concept_name"
    local build_dir="${POLYGLOT_CPP_CONCEPT_BUILD_DIR:-/tmp/polyglot-cpp-concepts-build}"
    local concept_target="${concept_name//\//_}"
    run_cpp_layer concepts "$build_dir" '^polyglot-concept$' \
      -R "^concept_${concept_target}_"
  fi
}

run_concept_nodejs() {
  local concept_name="$1"
  local -a test_files=()
  if [[ -d "concepts/$concept_name/nodejs" ]]; then
    mapfile -d '' test_files < <(
      find "concepts/$concept_name/nodejs" \
        -maxdepth 1 \
        -type f \
        -name 'test_[0-9][0-9]_*.mjs' \
        -print0 | sort -z
    )
    if [[ ${#test_files[@]} -eq 0 ]]; then
      echo "概念缺少 Node.js 测试: $concept_name" >&2
      exit 1
    fi
    printf '\n== %s / Node.js ==\n' "$concept_name"
    run_nodejs_files "${test_files[@]}"
  fi
}

run_concept() {
  local concept_name="${1:-}"
  validate_concept_name "$concept_name"
  run_concept_python "$concept_name"
  run_concept_cpp "$concept_name"
  run_concept_nodejs "$concept_name"
  run_concept_go "$concept_name"
}

validate_family_name() {
  local family_name="$1"
  if [[ ! "$family_name" =~ ^[0-9]{2}_[a-z0-9_]+$ ]]; then
    echo "章节名必须使用 NN_family 格式: $family_name" >&2
    exit 2
  fi
  if [[ ! -d "concepts/$family_name" ]]; then
    echo "概念章节不存在: concepts/$family_name" >&2
    exit 2
  fi
}

run_family() {
  local family_name="${1:-}"
  local -a python_test_files=()
  local -a nodejs_test_files=()
  local topic_directory
  local topic_count=0
  validate_family_name "$family_name"

  for topic_directory in "concepts/$family_name"/[0-9][0-9]_*; do
    if [[ ! -d "$topic_directory" ]]; then
      continue
    fi
    topic_count=$((topic_count + 1))
  done

  if ((topic_count == 0)); then
    echo "概念章节没有发现主题: concepts/$family_name" >&2
    exit 1
  fi

  mapfile -d '' python_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/python/test_[0-9][0-9]_*.py' \
      -print0 | sort -z
  )
  mapfile -d '' nodejs_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/nodejs/test_[0-9][0-9]_*.mjs' \
      -print0 | sort -z
  )

  if [[ ${#python_test_files[@]} -gt 0 ]]; then
    need_cmd python3
    printf '\n== %s / Python ==\n' "$family_name"
    python3 -m pytest --import-mode=importlib "${python_test_files[@]}"
  fi

  if find "concepts/$family_name" \
    -type f \
    -path '*/cpp/test_[0-9][0-9]_*.cpp' \
    -print \
    -quit | grep -q .; then
    printf '\n== %s / C++ ==\n' "$family_name"
    local build_dir="${POLYGLOT_CPP_CONCEPT_BUILD_DIR:-/tmp/polyglot-cpp-concepts-build}"
    run_cpp_layer concepts "$build_dir" '^polyglot-concept$' \
      -R "^concept_${family_name}_"
  fi

  if [[ ${#nodejs_test_files[@]} -gt 0 ]]; then
    printf '\n== %s / Node.js ==\n' "$family_name"
    run_nodejs_files "${nodejs_test_files[@]}"
  fi

  if find "concepts/$family_name" \
    -type f \
    -path '*/go/test_[0-9][0-9]_*_test.go' \
    -print \
    -quit | grep -q .; then
    check_go_version
    printf '\n== %s / Go ==\n' "$family_name"
    (
      cd concepts
      go test -count=1 "./$family_name/..."
    )
  fi
}

run_concepts() {
  local -a python_test_files=()
  local -a nodejs_test_files=()
  mapfile -d '' python_test_files < <(
    find concepts \
      -type f \
      -path '*/python/test_[0-9][0-9]_*.py' \
      -print0 | sort -z
  )
  mapfile -d '' nodejs_test_files < <(
    find concepts \
      -type f \
      -path '*/nodejs/test_[0-9][0-9]_*.mjs' \
      -print0 | sort -z
  )

  if [[ ${#python_test_files[@]} -gt 0 ]]; then
    need_cmd python3
    printf '\n== all concepts / Python ==\n'
    python3 -m pytest --import-mode=importlib "${python_test_files[@]}"
  fi

  if find concepts \
    -type f \
    -path '*/cpp/test_[0-9][0-9]_*.cpp' \
    -print \
    -quit | grep -q .; then
    printf '\n== all concepts / C++ ==\n'
    local build_dir="${POLYGLOT_CPP_CONCEPT_BUILD_DIR:-/tmp/polyglot-cpp-concepts-build}"
    run_cpp_layer concepts "$build_dir" '^polyglot-concept$'
  fi

  if [[ ${#nodejs_test_files[@]} -gt 0 ]]; then
    printf '\n== all concepts / Node.js ==\n'
    run_nodejs_files "${nodejs_test_files[@]}"
  fi

  if find concepts \
    -type f \
    -path '*/go/test_[0-9][0-9]_*_test.go' \
    -print \
    -quit | grep -q .; then
    check_go_version
    printf '\n== all concepts / Go ==\n'
    (
      cd concepts
      go test -count=1 ./...
      go vet ./...
    )
  fi
}

list_concepts() {
  local family_directory
  local topic_directory
  local language
  local extension
  local count
  local -a language_counts=()

  printf '%-38s %-46s %s\n' "FAMILY" "TOPIC" "LANGUAGES / TEST FILES"
  for family_directory in concepts/[0-9][0-9]_*; do
    if [[ ! -d "$family_directory" ]]; then
      continue
    fi
    for topic_directory in "$family_directory"/[0-9][0-9]_*; do
      if [[ ! -d "$topic_directory" ]]; then
        continue
      fi
      language_counts=()
      for language in python cpp nodejs go; do
        case "$language" in
          python)
            extension=py
            ;;
          cpp)
            extension=cpp
            ;;
          nodejs)
            extension=mjs
            ;;
          go)
            extension=go
            ;;
        esac
        if [[ ! -d "$topic_directory/$language" ]]; then
          continue
        fi
        count=$(
          find "$topic_directory/$language" \
            -maxdepth 1 \
            -type f \
            -name "$(
              if [[ "$language" == go ]]; then
                printf 'test_[0-9][0-9]_*_test.go'
              else
                printf 'test_[0-9][0-9]_*.%s' "$extension"
              fi
            )" \
            -print | wc -l | tr -d ' '
        )
        language_counts+=("$language:$count")
      done
      printf '%-38s %-46s %s\n' \
        "${family_directory##*/}" \
        "${topic_directory##*/}" \
        "${language_counts[*]}"
    done
  done
}

run_checks() {
  ./tools/check-structure.sh
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
    go|golang)
      shift
      run_go "$@"
      ;;
    concept)
      shift
      run_concept "$@"
      ;;
    family)
      shift
      run_family "$@"
      ;;
    concepts)
      shift
      run_concepts "$@"
      ;;
    list-concepts)
      shift
      list_concepts "$@"
      ;;
    check|structure|lint)
      shift
      run_checks "$@"
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
