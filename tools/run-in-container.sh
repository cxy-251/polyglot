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
  ./tools/run-in-container.sh r [test files...]
  ./tools/run-in-container.sh r-harness [test files...]
  ./tools/run-in-container.sh lua [test files...]
  ./tools/run-in-container.sh lua-harness [test files...]
  ./tools/run-in-container.sh ruby [test files...]
  ./tools/run-in-container.sh ruby-harness [test files...]
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

doctor_julia() {
  check_julia_version
  printf 'julia: '
  JULIA_DEPOT_PATH=/tmp/polyglot-julia-doctor-depot \
    JULIA_LOAD_PATH='@:@stdlib' \
    julia --startup-file=no --history-file=no --project=@stdlib --version
}

doctor_r() {
  check_r_version
  printf 'R: '
  R --vanilla --version | sed -n '1p'
  printf 'Rscript: '
  Rscript --version 2>&1 | sed -n '1p'
}

doctor_lua() {
  check_lua_version
  printf 'lua: '
  lua -E -v
  printf 'lua path: '
  command -v lua
  printf 'luac: '
  luac -v
  printf 'luac path: '
  command -v luac
  printf 'Lua headers: %s\n' /opt/polyglot/lua-5.5.0/include
  printf 'Lua library: %s\n' /opt/polyglot/lua-5.5.0/lib/liblua.a
  printf 'Lua module path: repository and per-test temporary directories only\n'
}

doctor_ruby() {
  check_ruby_version
  printf 'ruby: '
  ruby --version
  printf 'ruby path: '
  command -v ruby
  printf 'gem: '
  gem --version
  printf 'bundle: '
  bundle --version
  printf 'rake: '
  rake --version
  printf 'Ruby headers: '
  ruby --disable-gems -rrbconfig -e 'puts RbConfig::CONFIG.fetch("rubyhdrdir")'
  printf 'Ruby engine: '
  ruby --disable-gems -e 'puts RUBY_ENGINE'
  printf 'RubyGems/Bundler: isolated local paths only\n'
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
  if [[ ${#PLANNED_LANGUAGES[@]} -eq 0 ]]; then
    echo 'planned languages: (none)'
    return
  fi
  printf 'planned languages: %s\n' "${PLANNED_LANGUAGES[*]}"
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
      julia)
        doctor_julia
        ;;
      r)
        doctor_r
        ;;
      lua)
        doctor_lua
        ;;
      ruby)
        doctor_ruby
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
    "@stdlib" \
    "${POLYGLOT_JULIA_COURSE_DEPOT:-/tmp/polyglot-julia-course-depot}" \
    "${test_files[@]}"
}

run_julia_harness() {
  check_julia_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find harness/julia/tests \
        -maxdepth 1 \
        -type f \
        -name 'test_*.jl' \
        -print0 | sort -z
    )
  fi
  run_julia_files \
    "Julia harness" \
    "@stdlib" \
    "${POLYGLOT_JULIA_HARNESS_DEPOT:-/tmp/polyglot-julia-harness-depot}" \
    "${test_files[@]}"
}

check_r_version() {
  need_cmd R
  need_cmd Rscript

  local expected_version="4.6.1"
  local actual_version
  actual_version="$(Rscript --vanilla -e 'cat(as.character(getRversion()))')"
  if [[ "$actual_version" != "$expected_version" ]]; then
    echo "R 版本不匹配: 需要 $expected_version，实际 $actual_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh r。" >&2
    exit 1
  fi
}

run_r_files() {
  local label="$1"
  local sandbox_root="$2"
  shift 2
  local -a test_files=("$@")
  local test_file
  local test_sandbox

  if [[ ${#test_files[@]} -eq 0 ]]; then
    echo "$label 没有发现 R 测试文件。" >&2
    exit 1
  fi

  mkdir -p "$sandbox_root"
  printf '\n== %s ==\n' "$label"
  for test_file in "${test_files[@]}"; do
    if [[ ! -f "$test_file" ]]; then
      echo "R 测试文件不存在: $test_file" >&2
      exit 2
    fi

    test_sandbox="$(mktemp -d "$sandbox_root/test.XXXXXX")"
    mkdir -p \
      "$test_sandbox/library" \
      "$test_sandbox/tmp" \
      "$test_sandbox/user"
    if ! R_LIBS_USER="$test_sandbox/library" \
      R_USER="$test_sandbox/user" \
      TMPDIR="$test_sandbox/tmp" \
      R_ENVIRON_USER=/dev/null \
      R_PROFILE_USER=/dev/null \
      R_DEFAULT_PACKAGES='datasets,utils,grDevices,graphics,stats,methods' \
      TZ=UTC \
      LC_ALL=C.UTF-8 \
      Rscript \
        --vanilla \
        harness/r/support/run_test.R \
        "$test_file"; then
      echo "R 测试失败: $test_file" >&2
      rm -rf "$test_sandbox"
      exit 1
    fi
    rm -rf "$test_sandbox"
  done
  printf '%s: %d 个 R 测试文件通过。\n' "$label" "${#test_files[@]}"
}

prepare_r_assets() {
  local asset_root="$1"
  local need_package="$2"
  local need_native="$3"
  mkdir -p "$asset_root/library" "$asset_root/tmp" "$asset_root/user"

  if [[ "$need_package" == 1 ]]; then
    POLYGLOT_R_PACKAGE_LIBRARY="$(
      R_LIBS_USER="$asset_root/library" \
        R_USER="$asset_root/user" \
        TMPDIR="$asset_root/tmp" \
        R_ENVIRON_USER=/dev/null \
        R_PROFILE_USER=/dev/null \
        Rscript --vanilla -e '
          source("harness/r/support/package_helpers.R")
          root <- file.path(commandArgs(trailingOnly = TRUE)[[1L]], "package")
          dir.create(root)
          cat(install_polyglot_package(root)$library)
        ' "$asset_root"
    )"
    export POLYGLOT_R_PACKAGE_LIBRARY
  fi

  if [[ "$need_native" == 1 ]]; then
    POLYGLOT_R_NATIVE_LIBRARY="$(
      R_LIBS_USER="$asset_root/library" \
        R_USER="$asset_root/user" \
        TMPDIR="$asset_root/tmp" \
        R_ENVIRON_USER=/dev/null \
        R_PROFILE_USER=/dev/null \
        Rscript --vanilla -e '
          source("harness/r/support/native_helpers.R")
          root <- file.path(commandArgs(trailingOnly = TRUE)[[1L]], "native")
          dir.create(root)
          cat(build_polyglot_native(root))
        ' "$asset_root"
    )"
    export POLYGLOT_R_NATIVE_LIBRARY
  fi
}

run_r() {
  check_r_version
  local -a test_files=()
  local test_file
  local need_package=0
  local need_native=0
  local asset_root=""
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find languages/r \
        -type f \
        -name 'test_[0-9][0-9][0-9]_*.R' \
        -print0 | sort -z
    )
  fi
  for test_file in "${test_files[@]}"; do
    if grep -Fq "POLYGLOT_R_PACKAGE_LIBRARY" "$test_file"; then
      need_package=1
    fi
    if grep -Fq "POLYGLOT_R_NATIVE_LIBRARY" "$test_file"; then
      need_native=1
    fi
  done
  if [[ "$need_package" == 1 || "$need_native" == 1 ]]; then
    asset_root="$(mktemp -d /tmp/polyglot-r-course-assets.XXXXXX)"
    POLYGLOT_R_COURSE_ASSET_ROOT="$asset_root"
    export POLYGLOT_R_COURSE_ASSET_ROOT
    trap 'rm -rf "$POLYGLOT_R_COURSE_ASSET_ROOT"' EXIT
    prepare_r_assets "$asset_root" "$need_package" "$need_native"
  fi
  run_r_files \
    "R vertical course" \
    "${POLYGLOT_R_COURSE_ROOT:-/tmp/polyglot-r-course}" \
    "${test_files[@]}"
  if [[ -n "$asset_root" ]]; then
    rm -rf "$asset_root"
    unset POLYGLOT_R_COURSE_ASSET_ROOT POLYGLOT_R_PACKAGE_LIBRARY POLYGLOT_R_NATIVE_LIBRARY
    trap - EXIT
  fi
}

run_r_harness() {
  check_r_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find harness/r/tests \
        -maxdepth 1 \
        -type f \
        -name 'test_*.R' \
        -print0 | sort -z
    )
  fi
  run_r_files \
    "R harness" \
    "${POLYGLOT_R_HARNESS_ROOT:-/tmp/polyglot-r-harness}" \
    "${test_files[@]}"
}

check_lua_version() {
  need_cmd lua
  need_cmd luac

  local expected_version="5.5.0"
  local actual_lua_version
  local actual_luac_version
  actual_lua_version="$(lua -E -v 2>&1 | awk '{print $2}')"
  actual_luac_version="$(luac -v 2>&1 | awk '{print $2}')"
  if [[ "$actual_lua_version" != "$expected_version" ]]; then
    echo "Lua 版本不匹配: 需要 $expected_version，实际 $actual_lua_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh lua。" >&2
    exit 1
  fi
  if [[ "$actual_luac_version" != "$expected_version" ]]; then
    echo "luac 版本不匹配: 需要 $expected_version，实际 $actual_luac_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh lua。" >&2
    exit 1
  fi
  if [[ ! -f /opt/polyglot/lua-5.5.0/include/lua.h ]] || \
    [[ ! -f /opt/polyglot/lua-5.5.0/lib/liblua.a ]]; then
    echo "Lua C 工具链不完整: 需要 5.5.0 头文件与 liblua.a" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh lua。" >&2
    exit 1
  fi
}

build_lua_c_api() {
  local build_directory="$1"
  need_cmd cc
  mkdir -p "$build_directory"
  make \
    --no-print-directory \
    -C harness/lua/c_api \
    LUA_HOME=/opt/polyglot/lua-5.5.0 \
    BUILD_DIR="$build_directory" \
    all
}

run_lua_files() {
  local label="$1"
  local sandbox_root="$2"
  shift 2
  local -a test_files=("$@")
  local run_sandbox
  local test_sandbox
  local test_file
  local support_path
  local c_module_path
  local needs_c_api=0

  if [[ ${#test_files[@]} -eq 0 ]]; then
    echo "$label 没有发现 Lua 测试文件。" >&2
    exit 1
  fi

  mkdir -p "$sandbox_root"
  run_sandbox="$(mktemp -d "$sandbox_root/run.XXXXXX")"
  for test_file in "${test_files[@]}"; do
    if grep -Eq \
      'polyglot_native|support[.]c_api|POLYGLOT_LUA_C_API_HOST' \
      "$test_file"; then
      needs_c_api=1
      break
    fi
  done
  if ((needs_c_api)); then
    build_lua_c_api "$run_sandbox/c-api"
  fi
  support_path="$ROOT/harness/lua/?.lua;$ROOT/harness/lua/?/init.lua"
  support_path+=";$ROOT/languages/lua/fixtures/modules/?.lua"
  c_module_path="$run_sandbox/c-api/?.so"

  printf '\n== %s ==\n' "$label"
  for test_file in "${test_files[@]}"; do
    if [[ ! -f "$test_file" ]]; then
      echo "Lua 测试文件不存在: $test_file" >&2
      rm -rf "$run_sandbox"
      exit 2
    fi

    test_sandbox="$(mktemp -d "$run_sandbox/test.XXXXXX")"
    mkdir -p "$test_sandbox/home" "$test_sandbox/tmp"
    if ! env \
      -u LUA_INIT \
      -u LUA_INIT_5_5 \
      -u LUA_PATH \
      -u LUA_PATH_5_5 \
      -u LUA_CPATH \
      -u LUA_CPATH_5_5 \
      HOME="$test_sandbox/home" \
      TMPDIR="$test_sandbox/tmp" \
      TZ=UTC \
      LC_ALL=C.UTF-8 \
      POLYGLOT_LUA_TEST_TMP="$test_sandbox/tmp" \
      POLYGLOT_LUA_PATH="$support_path" \
      POLYGLOT_LUA_CPATH="$c_module_path" \
      POLYGLOT_LUA_C_API_HOST="$run_sandbox/c-api/polyglot_lua_host" \
      lua \
        -E \
        -e '
          package.path = assert(os.getenv("POLYGLOT_LUA_PATH"))
          package.cpath = assert(os.getenv("POLYGLOT_LUA_CPATH"))
        ' \
        "$test_file"; then
      echo "Lua 测试失败: $test_file" >&2
      rm -rf "$run_sandbox"
      exit 1
    fi
    rm -rf "$test_sandbox"
  done
  rm -rf "$run_sandbox"
  printf '%s: %d 个 Lua 测试文件通过。\n' "$label" "${#test_files[@]}"
}

run_lua() {
  check_lua_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find languages/lua \
        -type f \
        -name 'test_[0-9][0-9][0-9]_*.lua' \
        -print0 | sort -z
    )
  fi
  run_lua_files \
    "Lua vertical course" \
    "${POLYGLOT_LUA_COURSE_ROOT:-/tmp/polyglot-lua-course}" \
    "${test_files[@]}"
}

run_lua_harness() {
  check_lua_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find harness/lua/tests \
        -type f \
        -name 'test_*.lua' \
        -print0 | sort -z
    )
  fi
  run_lua_files \
    "Lua harness" \
    "${POLYGLOT_LUA_HARNESS_ROOT:-/tmp/polyglot-lua-harness}" \
    "${test_files[@]}"
}

check_ruby_version() {
  need_cmd ruby
  need_cmd gem
  need_cmd bundle
  need_cmd rake

  local expected_version="4.0.6"
  local actual_version
  local actual_engine
  local ruby_header_directory
  actual_version="$(ruby --disable-gems -e 'print RUBY_VERSION')"
  actual_engine="$(ruby --disable-gems -e 'print RUBY_ENGINE')"
  ruby_header_directory="$(
    ruby --disable-gems -rrbconfig -e 'print RbConfig::CONFIG.fetch("rubyhdrdir")'
  )"
  if [[ "$actual_version" != "$expected_version" ]] || [[ "$actual_engine" != ruby ]]; then
    echo "Ruby 版本不匹配: 需要 CRuby $expected_version，实际 $actual_engine $actual_version" >&2
    echo "请在 ohdev 中运行 ./tools/bootstrap-language-toolchains-in-container.sh ruby。" >&2
    exit 1
  fi
  if [[ "$ruby_header_directory" != /opt/polyglot/ruby-4.0.6/include/ruby-4.0.0 ]]; then
    echo "Ruby C Extension 头文件不是锁定的 4.0.6 安装: $ruby_header_directory" >&2
    exit 1
  fi
}

build_ruby_c_extension() {
  local build_directory="$1"
  local source_directory="$ROOT/harness/ruby/c_extension"
  need_cmd cc
  need_cmd make
  mkdir -p "$build_directory"
  (
    cd "$build_directory"
    ruby "$source_directory/extconf.rb"
    make V=1
  )
}

run_ruby_files() {
  local label="$1"
  local sandbox_root="$2"
  shift 2
  local -a test_files=("$@")
  local run_sandbox
  local test_sandbox
  local test_file
  local default_gem_directory
  local requires_native_extension=false

  if [[ ${#test_files[@]} -eq 0 ]]; then
    echo "$label 没有发现 Ruby 测试文件。" >&2
    exit 1
  fi

  mkdir -p "$sandbox_root"
  run_sandbox="$(mktemp -d "$sandbox_root/run.XXXXXX")"
  for test_file in "${test_files[@]}"; do
    if grep -Fq 'require "polyglot_native"' "$test_file"; then
      requires_native_extension=true
      break
    fi
  done
  if [[ "$requires_native_extension" == true ]]; then
    build_ruby_c_extension "$run_sandbox/c-extension"
  else
    mkdir -p "$run_sandbox/c-extension"
  fi
  default_gem_directory="$(
    ruby -rrubygems -e 'print Gem.default_dir'
  )"

  printf '\n== %s ==\n' "$label"
  for test_file in "${test_files[@]}"; do
    if [[ ! -f "$test_file" ]]; then
      echo "Ruby 测试文件不存在: $test_file" >&2
      rm -rf "$run_sandbox"
      exit 2
    fi

    test_sandbox="$(mktemp -d "$run_sandbox/test.XXXXXX")"
    mkdir -p \
      "$test_sandbox/home" \
      "$test_sandbox/tmp" \
      "$test_sandbox/gems" \
      "$test_sandbox/bundle"
    if ! env \
      -u RUBYOPT \
      -u RUBYLIB \
      -u GEM_HOME \
      -u GEM_PATH \
      -u BUNDLE_GEMFILE \
      -u BUNDLE_PATH \
      -u BUNDLE_APP_CONFIG \
      HOME="$test_sandbox/home" \
      TMPDIR="$test_sandbox/tmp" \
      GEM_HOME="$test_sandbox/gems" \
      GEM_PATH="$test_sandbox/gems:$default_gem_directory" \
      GEMRC=/dev/null \
      BUNDLE_USER_HOME="$test_sandbox/bundle" \
      BUNDLE_USER_CONFIG="$test_sandbox/bundle/config" \
      BUNDLE_USER_CACHE="$test_sandbox/bundle/cache" \
      BUNDLE_USER_PLUGIN="$test_sandbox/bundle/plugin" \
      BUNDLE_DISABLE_VERSION_CHECK=true \
      BUNDLE_SILENCE_ROOT_WARNING=true \
      BUNDLE_ALLOW_OFFLINE_INSTALL=true \
      TZ=UTC \
      LC_ALL=C.UTF-8 \
      POLYGLOT_RUBY_TEST_TMP="$test_sandbox/tmp" \
      POLYGLOT_RUBY_GEM_HOME="$test_sandbox/gems" \
      POLYGLOT_RUBY_BUNDLE_HOME="$test_sandbox/bundle" \
      POLYGLOT_RUBY_EXTENSION_DIR="$run_sandbox/c-extension" \
      ruby \
        --disable-did_you_mean \
        --disable-error_highlight \
        -W:no-experimental \
        -I "$ROOT/harness/ruby/support" \
        -I "$run_sandbox/c-extension" \
        -cw \
        "$test_file" >/dev/null; then
      echo "Ruby 语法或 warning 检查失败: $test_file" >&2
      rm -rf "$run_sandbox"
      exit 1
    fi
    if ! env \
      -u RUBYOPT \
      -u RUBYLIB \
      -u GEM_HOME \
      -u GEM_PATH \
      -u BUNDLE_GEMFILE \
      -u BUNDLE_PATH \
      -u BUNDLE_APP_CONFIG \
      HOME="$test_sandbox/home" \
      TMPDIR="$test_sandbox/tmp" \
      GEM_HOME="$test_sandbox/gems" \
      GEM_PATH="$test_sandbox/gems:$default_gem_directory" \
      GEMRC=/dev/null \
      BUNDLE_USER_HOME="$test_sandbox/bundle" \
      BUNDLE_USER_CONFIG="$test_sandbox/bundle/config" \
      BUNDLE_USER_CACHE="$test_sandbox/bundle/cache" \
      BUNDLE_USER_PLUGIN="$test_sandbox/bundle/plugin" \
      BUNDLE_DISABLE_VERSION_CHECK=true \
      BUNDLE_SILENCE_ROOT_WARNING=true \
      BUNDLE_ALLOW_OFFLINE_INSTALL=true \
      TZ=UTC \
      LC_ALL=C.UTF-8 \
      POLYGLOT_RUBY_TEST_TMP="$test_sandbox/tmp" \
      POLYGLOT_RUBY_GEM_HOME="$test_sandbox/gems" \
      POLYGLOT_RUBY_BUNDLE_HOME="$test_sandbox/bundle" \
      POLYGLOT_RUBY_EXTENSION_DIR="$run_sandbox/c-extension" \
      ruby \
        --disable-did_you_mean \
        --disable-error_highlight \
        -W:deprecated \
        -W:no-experimental \
        -I "$ROOT/harness/ruby/support" \
        -I "$run_sandbox/c-extension" \
        "$test_file"; then
      echo "Ruby 测试失败: $test_file" >&2
      rm -rf "$run_sandbox"
      exit 1
    fi
    rm -rf "$test_sandbox"
  done
  rm -rf "$run_sandbox"
  printf '%s: %d 个 Ruby 测试文件通过。\n' "$label" "${#test_files[@]}"
}

run_ruby() {
  check_ruby_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find languages/ruby \
        -type f \
        -name 'test_[0-9][0-9][0-9]_*.rb' \
        -print0 | sort -z
    )
  fi
  run_ruby_files \
    "Ruby vertical course" \
    "${POLYGLOT_RUBY_COURSE_ROOT:-/tmp/polyglot-ruby-course}" \
    "${test_files[@]}"
}

run_ruby_harness() {
  check_ruby_version
  local -a test_files=()
  if [[ $# -gt 0 ]]; then
    test_files=("$@")
  else
    mapfile -d '' test_files < <(
      find harness/ruby/tests \
        -maxdepth 1 \
        -type f \
        -name 'test_*.rb' \
        -print0 | sort -z
    )
  fi
  run_ruby_files \
    "Ruby harness and integration" \
    "${POLYGLOT_RUBY_HARNESS_ROOT:-/tmp/polyglot-ruby-harness}" \
    "${test_files[@]}"
}

run_rust() {
  check_rust_version
  local target_directory="${POLYGLOT_RUST_COURSE_TARGET_DIR:-/tmp/polyglot-rust-course-target}"
  printf '\n== Rust vertical course ==\n'
  CARGO_TARGET_DIR="$target_directory" cargo fmt --manifest-path Cargo.toml --all --check
  CARGO_TARGET_DIR="$target_directory" \
    cargo clippy --manifest-path Cargo.toml --test course --all-features -- -D warnings
  CARGO_TARGET_DIR="$target_directory" \
    cargo test --manifest-path Cargo.toml --test course "$@"
}

run_rust_harness() {
  check_rust_version
  local target_directory="${POLYGLOT_RUST_HARNESS_TARGET_DIR:-/tmp/polyglot-rust-harness-target}"
  printf '\n== Rust harness and integration ==\n'
  CARGO_TARGET_DIR="$target_directory" cargo fmt --manifest-path Cargo.toml --all --check
  CARGO_TARGET_DIR="$target_directory" \
    cargo clippy --manifest-path Cargo.toml --all-targets --all-features -- -D warnings
  CARGO_TARGET_DIR="$target_directory" \
    cargo test --manifest-path Cargo.toml --test harness "$@"
  CARGO_TARGET_DIR="$target_directory" cargo test --manifest-path Cargo.toml --doc
}

run_rust_concepts() {
  check_rust_version
  local target_directory="${POLYGLOT_RUST_CONCEPT_TARGET_DIR:-/tmp/polyglot-rust-concepts-target}"
  printf '\n== Rust horizontal concepts ==\n'
  CARGO_TARGET_DIR="$target_directory" \
    cargo fmt --manifest-path concepts/Cargo.toml --all --check
  CARGO_TARGET_DIR="$target_directory" \
    cargo clippy --manifest-path concepts/Cargo.toml --all-targets -- -D warnings
  CARGO_TARGET_DIR="$target_directory" \
    cargo test --manifest-path concepts/Cargo.toml --test concepts "$@"
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

run_concept_julia() {
  local concept_name="$1"
  local -a test_files=()
  if [[ -d "concepts/$concept_name/julia" ]]; then
    mapfile -d '' test_files < <(
      find "concepts/$concept_name/julia" \
        -maxdepth 1 \
        -type f \
        -name 'test_[0-9][0-9]_*.jl' \
        -print0 | sort -z
    )
    check_julia_version
    run_julia_files \
      "$concept_name / Julia" \
      "concepts" \
      "${POLYGLOT_JULIA_CONCEPT_DEPOT:-/tmp/polyglot-julia-concepts-depot}" \
      "${test_files[@]}"
  fi
}

run_concept_r() {
  local concept_name="$1"
  local -a r_test_files=()
  if [[ -d "concepts/$concept_name/r" ]]; then
    mapfile -d '' r_test_files < <(
      find "concepts/$concept_name/r" \
        -maxdepth 1 \
        -type f \
        -name 'test_[0-9][0-9]_*.R' \
        -print0 | sort -z
    )
    check_r_version
    run_r_files \
      "$concept_name / R" \
      "${POLYGLOT_R_CONCEPT_ROOT:-/tmp/polyglot-r-concepts}" \
      "${r_test_files[@]}"
  fi
}

run_concept_lua() {
  local concept_name="$1"
  local -a lua_test_files=()
  if [[ -d "concepts/$concept_name/lua" ]]; then
    mapfile -d '' lua_test_files < <(
      find "concepts/$concept_name/lua" \
        -maxdepth 1 \
        -type f \
        -name 'test_[0-9][0-9]_*.lua' \
        -print0 | sort -z
    )
    check_lua_version
    run_lua_files \
      "$concept_name / Lua" \
      "${POLYGLOT_LUA_CONCEPT_ROOT:-/tmp/polyglot-lua-concepts}" \
      "${lua_test_files[@]}"
  fi
}

run_concept_ruby() {
  local concept_name="$1"
  local -a ruby_test_files=()
  if [[ -d "concepts/$concept_name/ruby" ]]; then
    mapfile -d '' ruby_test_files < <(
      find "concepts/$concept_name/ruby" \
        -maxdepth 1 \
        -type f \
        -name 'test_[0-9][0-9]_*.rb' \
        -print0 | sort -z
    )
    check_ruby_version
    run_ruby_files \
      "$concept_name / Ruby" \
      "${POLYGLOT_RUBY_CONCEPT_ROOT:-/tmp/polyglot-ruby-concepts}" \
      "${ruby_test_files[@]}"
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

run_family_julia() {
  local family_name="$1"
  local -a julia_test_files=()
  mapfile -d '' julia_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/julia/test_[0-9][0-9]_*.jl' \
      -print0 | sort -z
  )
  if [[ ${#julia_test_files[@]} -gt 0 ]]; then
    check_julia_version
    run_julia_files \
      "$family_name / Julia" \
      "concepts" \
      "${POLYGLOT_JULIA_CONCEPT_DEPOT:-/tmp/polyglot-julia-concepts-depot}" \
      "${julia_test_files[@]}"
  fi
}

run_family_r() {
  local family_name="$1"
  local -a r_test_files=()
  mapfile -d '' r_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/r/test_[0-9][0-9]_*.R' \
      -print0 | sort -z
  )
  if [[ ${#r_test_files[@]} -gt 0 ]]; then
    check_r_version
    run_r_files \
      "$family_name / R" \
      "${POLYGLOT_R_CONCEPT_ROOT:-/tmp/polyglot-r-concepts}" \
      "${r_test_files[@]}"
  fi
}

run_family_lua() {
  local family_name="$1"
  local -a lua_test_files=()
  mapfile -d '' lua_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/lua/test_[0-9][0-9]_*.lua' \
      -print0 | sort -z
  )
  if [[ ${#lua_test_files[@]} -gt 0 ]]; then
    check_lua_version
    run_lua_files \
      "$family_name / Lua" \
      "${POLYGLOT_LUA_CONCEPT_ROOT:-/tmp/polyglot-lua-concepts}" \
      "${lua_test_files[@]}"
  fi
}

run_family_ruby() {
  local family_name="$1"
  local -a ruby_test_files=()
  mapfile -d '' ruby_test_files < <(
    find "concepts/$family_name" \
      -type f \
      -path '*/ruby/test_[0-9][0-9]_*.rb' \
      -print0 | sort -z
  )
  if [[ ${#ruby_test_files[@]} -gt 0 ]]; then
    check_ruby_version
    run_ruby_files \
      "$family_name / Ruby" \
      "${POLYGLOT_RUBY_CONCEPT_ROOT:-/tmp/polyglot-ruby-concepts}" \
      "${ruby_test_files[@]}"
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

run_all_concepts_julia() {
  local -a julia_test_files=()
  mapfile -d '' julia_test_files < <(
    find concepts \
      -type f \
      -path '*/julia/test_[0-9][0-9]_*.jl' \
      -print0 | sort -z
  )
  if [[ ${#julia_test_files[@]} -gt 0 ]]; then
    check_julia_version
    run_julia_files \
      "all concepts / Julia" \
      "concepts" \
      "${POLYGLOT_JULIA_CONCEPT_DEPOT:-/tmp/polyglot-julia-concepts-depot}" \
      "${julia_test_files[@]}"
  fi
}

run_all_concepts_r() {
  local -a r_test_files=()
  mapfile -d '' r_test_files < <(
    find concepts \
      -type f \
      -path '*/r/test_[0-9][0-9]_*.R' \
      -print0 | sort -z
  )
  if [[ ${#r_test_files[@]} -gt 0 ]]; then
    check_r_version
    run_r_files \
      "all concepts / R" \
      "${POLYGLOT_R_CONCEPT_ROOT:-/tmp/polyglot-r-concepts}" \
      "${r_test_files[@]}"
  fi
}

run_all_concepts_lua() {
  local -a lua_test_files=()
  mapfile -d '' lua_test_files < <(
    find concepts \
      -type f \
      -path '*/lua/test_[0-9][0-9]_*.lua' \
      -print0 | sort -z
  )
  if [[ ${#lua_test_files[@]} -gt 0 ]]; then
    check_lua_version
    run_lua_files \
      "all concepts / Lua" \
      "${POLYGLOT_LUA_CONCEPT_ROOT:-/tmp/polyglot-lua-concepts}" \
      "${lua_test_files[@]}"
  fi
}

run_all_concepts_ruby() {
  local -a ruby_test_files=()
  mapfile -d '' ruby_test_files < <(
    find concepts \
      -type f \
      -path '*/ruby/test_[0-9][0-9]_*.rb' \
      -print0 | sort -z
  )
  if [[ ${#ruby_test_files[@]} -gt 0 ]]; then
    check_ruby_version
    run_ruby_files \
      "all concepts / Ruby" \
      "${POLYGLOT_RUBY_CONCEPT_ROOT:-/tmp/polyglot-ruby-concepts}" \
      "${ruby_test_files[@]}"
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
          julia)
            extension=jl
            ;;
          r)
            extension=R
            ;;
          lua)
            extension=lua
            ;;
          ruby)
            extension=rb
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
    rust-harness)
      shift
      run_rust_harness "$@"
      ;;
    rust-concepts)
      shift
      run_rust_concepts "$@"
      ;;
    julia|jl)
      shift
      run_julia "$@"
      ;;
    julia-harness)
      shift
      run_julia_harness "$@"
      ;;
    r|R)
      shift
      run_r "$@"
      ;;
    r-harness)
      shift
      run_r_harness "$@"
      ;;
    lua)
      shift
      run_lua "$@"
      ;;
    lua-harness)
      shift
      run_lua_harness "$@"
      ;;
    ruby|rb)
      shift
      run_ruby "$@"
      ;;
    ruby-harness)
      shift
      run_ruby_harness "$@"
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
