#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source "$ROOT/tools/language-state.sh"

usage() {
  cat <<'EOF'
Usage:
  ./tools/run-in-container.sh doctor [planned]
  ./tools/run-in-container.sh python [pytest arguments...]
  ./tools/run-in-container.sh cpp [ctest arguments...]
  ./tools/run-in-container.sh nodejs [node --test arguments or test files...]
  ./tools/run-in-container.sh go [go test arguments...]
  ./tools/run-in-container.sh rust [cargo test arguments...]
  ./tools/run-in-container.sh julia [test files...]
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

doctor_python() {
  need_cmd python3
  printf 'python: '
  python3 --version
  printf 'pytest: '
  python3 -m pytest --version
}

doctor_cpp() {
  need_cmd g++
  need_cmd cmake
  need_cmd ctest
  printf 'c++: '
  g++ --version | sed -n '1p'
  printf 'cmake: '
  cmake --version | sed -n '1p'
  printf 'ctest: '
  ctest --version | sed -n '1p'
}

doctor_nodejs() {
  need_cmd node
  need_cmd npm
  printf 'node: '
  node --version
  printf 'npm: '
  npm --version
}

doctor_go() {
  need_cmd go
  need_cmd gofmt
  printf 'go: '
  go version
  printf 'go env: '
  go env GOOS GOARCH GOROOT GOWORK | paste -sd ' ' -
  printf 'gofmt: '
  command -v gofmt
  printf 'go vet: '
  go help vet >/dev/null
  echo available
}

doctor_rust() {
  check_rust_version
  printf 'rustc: '
  rustc --version
  printf 'cargo: '
  cargo --version
  printf 'rustfmt: '
  rustfmt --version
  printf 'clippy: '
  cargo clippy --version
}

optional_version() {
  local label="$1"
  local command_name="$2"
  shift 2
  printf '%s: ' "$label"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo 'unavailable (planned_paused)'
    return
  fi

  local output
  if output=$("$@" 2>&1); then
    printf '%s\n' "${output%%$'\n'*}"
  else
    printf 'available, but version check failed: %s\n' "${output%%$'\n'*}"
  fi
}

doctor_planned() {
  printf 'planned languages: %s\n' "${PLANNED_LANGUAGES[*]}"
  optional_version julia julia julia --startup-file=no --history-file=no --version
  optional_version R R R --version
  optional_version Rscript Rscript Rscript --version
}

doctor() {
  local mode="${1:-active}"
  if [[ $# -gt 1 || "$mode" != active && "$mode" != planned ]]; then
    echo "doctor 只接受可选参数 planned" >&2
    exit 2
  fi

  printf 'workspace: %s\n' "$ROOT"
  printf 'active languages: %s\n' "${ACTIVE_LANGUAGES[*]}"
  local language
  for language in "${ACTIVE_LANGUAGES[@]}"; do
    case "$language" in
      python)
        doctor_python
        ;;
      cpp)
        doctor_cpp
        ;;
      nodejs)
        doctor_nodejs
        ;;
      go)
        doctor_go
        ;;
      rust)
        doctor_rust
        ;;
      *)
        echo "doctor 缺少 active language 检查实现: $language" >&2
        exit 2
        ;;
    esac
  done

  if [[ "$mode" == planned ]]; then
    doctor_planned
  fi
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

check_rust_version() {
  need_cmd rustc
  need_cmd cargo
  need_cmd rustfmt

  local expected_version="1.97.1"
  local actual_rustc_version
  local actual_cargo_version
  actual_rustc_version="$(rustc --version | awk '{print $2}')"
  actual_cargo_version="$(cargo --version | awk '{print $2}')"
  if [[ "$actual_rustc_version" != "$expected_version" ]]; then
    echo "rustc 版本不匹配: 需要 $expected_version，实际 $actual_rustc_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh rust。" >&2
    exit 1
  fi
  if [[ "$actual_cargo_version" != "$expected_version" ]]; then
    echo "Cargo 版本不匹配: 需要 $expected_version，实际 $actual_cargo_version" >&2
    exit 1
  fi
}

check_julia_version() {
  need_cmd julia

  local expected_version="1.12.6"
  local actual_version
  actual_version=$(
    JULIA_DEPOT_PATH=/tmp/polyglot-julia-version-depot \
      JULIA_LOAD_PATH='@:@stdlib' \
      julia \
        --startup-file=no \
        --history-file=no \
        --project=@stdlib \
        -e 'print(VERSION)'
  )
  if [[ "$actual_version" != "$expected_version" ]]; then
    echo "Julia 版本不匹配: 需要 $expected_version，实际 $actual_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh julia。" >&2
    exit 1
  fi
}

run_julia_files() {
  local label="$1"
  local project_directory="$2"
  local depot_directory="$3"
  shift 3
  local -a test_files=("$@")
  local test_file

  if [[ ${#test_files[@]} -eq 0 ]]; then
    echo "$label 没有发现 Julia 测试文件。" >&2
    exit 1
  fi

  mkdir -p "$depot_directory"
  printf '\n== %s ==\n' "$label"
  for test_file in "${test_files[@]}"; do
    if [[ ! -f "$test_file" ]]; then
      echo "Julia 测试文件不存在: $test_file" >&2
      exit 2
    fi
    JULIA_DEPOT_PATH="$depot_directory" \
      JULIA_LOAD_PATH='@:@stdlib' \
      JULIA_PKG_PRECOMPILE_AUTO=0 \
      julia \
        --startup-file=no \
        --history-file=no \
        --project="$project_directory" \
        --depwarn=error \
        --check-bounds=yes \
        --threads=2,0 \
        --color=no \
        "$test_file"
  done
  printf '%s: %d 个 Julia 测试文件通过。\n' "$label" "${#test_files[@]}"
}

run_julia() {
  check_julia_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find languages/julia \
        -type f \
        -name 'test_[0-9][0-9][0-9]_*.jl' \
        -print0 | sort -z
    )
  fi
  run_julia_files \
    "Julia vertical course" \
    "languages/julia" \
    "${POLYGLOT_JULIA_COURSE_DEPOT:-/tmp/polyglot-julia-course-depot}" \
    "${test_files[@]}"
}

run_rust() {
  check_rust_version
  local target_directory="${POLYGLOT_RUST_COURSE_TARGET_DIR:-/tmp/polyglot-rust-course-target}"
  printf '\n== Rust vertical course ==\n'
  CARGO_TARGET_DIR="$target_directory" cargo fmt --all --check
  CARGO_TARGET_DIR="$target_directory" \
    cargo clippy --workspace --all-targets --all-features -- -D warnings
  CARGO_TARGET_DIR="$target_directory" cargo test --workspace "$@"
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

run_concept_rust() {
  local concept_name="$1"
  if [[ -d "concepts/$concept_name/rust" ]]; then
    check_rust_version
    local family_number="${concept_name%%_*}"
    local topic_name="${concept_name#*/}"
    local topic_number="${topic_name%%_*}"
    local target_directory="${POLYGLOT_RUST_CONCEPT_TARGET_DIR:-/tmp/polyglot-rust-concepts-target}"
    printf '\n== %s / Rust ==\n' "$concept_name"
    CARGO_TARGET_DIR="$target_directory" \
      cargo test --manifest-path concepts/Cargo.toml --test concepts \
      "concept_${family_number}_${topic_number}_"
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
  local language
  validate_concept_name "$concept_name"
  for language in "${ACTIVE_LANGUAGES[@]}"; do
    run_concept_language "$language" "$concept_name"
  done
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

run_family_python() {
  local family_name="$1"
  local -a python_test_files=()
  mapfile -d '' python_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/python/test_[0-9][0-9]_*.py' \
      -print0 | sort -z
  )

  if [[ ${#python_test_files[@]} -gt 0 ]]; then
    need_cmd python3
    printf '\n== %s / Python ==\n' "$family_name"
    python3 -m pytest --import-mode=importlib "${python_test_files[@]}"
  fi
}

run_family_cpp() {
  local family_name="$1"
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
}

run_family_nodejs() {
  local family_name="$1"
  local -a nodejs_test_files=()
  mapfile -d '' nodejs_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/nodejs/test_[0-9][0-9]_*.mjs' \
      -print0 | sort -z
  )
  if [[ ${#nodejs_test_files[@]} -gt 0 ]]; then
    printf '\n== %s / Node.js ==\n' "$family_name"
    run_nodejs_files "${nodejs_test_files[@]}"
  fi
}

run_family_go() {
  local family_name="$1"
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

run_family_rust() {
  local family_name="$1"
  if find "concepts/$family_name" \
    -type f \
    -path '*/rust/test_[0-9][0-9]_*.rs' \
    -print \
    -quit | grep -q .; then
    check_rust_version
    local family_number="${family_name%%_*}"
    local target_directory="${POLYGLOT_RUST_CONCEPT_TARGET_DIR:-/tmp/polyglot-rust-concepts-target}"
    printf '\n== %s / Rust ==\n' "$family_name"
    CARGO_TARGET_DIR="$target_directory" \
      cargo test --manifest-path concepts/Cargo.toml --test concepts \
      "concept_${family_number}_"
  fi
}

run_all_concepts_python() {
  local -a python_test_files=()
  mapfile -d '' python_test_files < <(
    find concepts \
      -type f \
      -path '*/python/test_[0-9][0-9]_*.py' \
      -print0 | sort -z
  )

  if [[ ${#python_test_files[@]} -gt 0 ]]; then
    need_cmd python3
    printf '\n== all concepts / Python ==\n'
    python3 -m pytest --import-mode=importlib "${python_test_files[@]}"
  fi
}

run_all_concepts_cpp() {
  if find concepts \
    -type f \
    -path '*/cpp/test_[0-9][0-9]_*.cpp' \
    -print \
    -quit | grep -q .; then
    printf '\n== all concepts / C++ ==\n'
    local build_dir="${POLYGLOT_CPP_CONCEPT_BUILD_DIR:-/tmp/polyglot-cpp-concepts-build}"
    run_cpp_layer concepts "$build_dir" '^polyglot-concept$'
  fi
}

run_all_concepts_nodejs() {
  local -a nodejs_test_files=()
  mapfile -d '' nodejs_test_files < <(
    find concepts \
      -type f \
      -path '*/nodejs/test_[0-9][0-9]_*.mjs' \
      -print0 | sort -z
  )
  if [[ ${#nodejs_test_files[@]} -gt 0 ]]; then
    printf '\n== all concepts / Node.js ==\n'
    run_nodejs_files "${nodejs_test_files[@]}"
  fi
}

run_all_concepts_go() {
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

run_all_concepts_rust() {
  if find concepts \
    -type f \
    -path '*/rust/test_[0-9][0-9]_*.rs' \
    -print \
    -quit | grep -q .; then
    check_rust_version
    local target_directory="${POLYGLOT_RUST_CONCEPT_TARGET_DIR:-/tmp/polyglot-rust-concepts-target}"
    printf '\n== all concepts / Rust ==\n'
    cargo fmt --manifest-path concepts/Cargo.toml --all -- --check
    CARGO_TARGET_DIR="$target_directory" \
      cargo clippy --manifest-path concepts/Cargo.toml --all-targets --all-features -- -D warnings
    CARGO_TARGET_DIR="$target_directory" cargo test --manifest-path concepts/Cargo.toml
  fi
}

run_concept_language() {
  run_concept_scope_for_language concept "$1" "$2"
}

run_family_language() {
  run_concept_scope_for_language family "$1" "$2"
}

run_all_concepts_language() {
  run_concept_scope_for_language all_concepts "$1"
}

run_concept_scope_for_language() {
  local scope="$1"
  local language="$2"
  shift 2
  local runner="run_${scope}_${language}"
  if ! declare -F "$runner" >/dev/null; then
    echo "active language 缺少 ${scope} 横向运行器: $language" >&2
    exit 1
  fi
  "$runner" "$@"
}

run_family() {
  local family_name="${1:-}"
  local topic_directory
  local topic_count=0
  local language
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

  for language in "${ACTIVE_LANGUAGES[@]}"; do
    run_family_language "$language" "$family_name"
  done
}

run_concepts() {
  local language
  for language in "${ACTIVE_LANGUAGES[@]}"; do
    run_all_concepts_language "$language"
  done
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
      for language in "${ACTIVE_LANGUAGES[@]}"; do
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
          rust)
            extension=rs
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
      shift
      doctor "$@"
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
    rust|rs)
      shift
      run_rust "$@"
      ;;
    julia|jl)
      shift
      run_julia "$@"
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
