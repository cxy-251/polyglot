#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source "$ROOT/tools/language-state.sh"

readonly MAX_LINE_LENGTH=120
failure_count=0

report_failure() {
  printf '结构检查失败: %s\n' "$*" >&2
  failure_count=$((failure_count + 1))
}

project_language_ids() {
  local status="$1"
  python3 - "$status" <<'PY'
import json
import sys

with open("project.json", encoding="utf-8") as project_file:
    project = json.load(project_file)

print(" ".join(
    language["id"]
    for language in project["languages"]
    if language["status"] == sys.argv[1]
))
PY
}

check_active_language_state() {
  local expected_active="python cpp nodejs go rust julia r lua ruby"
  local configured_active="${ACTIVE_LANGUAGES[*]}"
  local configured_planned="${PLANNED_LANGUAGES[*]}"
  local project_active
  local project_active_count
  local project_planned

  if [[ "$configured_active" != "$expected_active" ]]; then
    report_failure "稳定 active language 集合错误: $configured_active"
  fi

  project_active=$(project_language_ids active)
  project_planned=$(project_language_ids planned_paused)
  project_active_count=$(
    python3 -c 'import json; print(json.load(open("project.json"))["active_language_count"])'
  )

  if [[ "$project_active" != "$configured_active" ]]; then
    report_failure "project.json active language 与运行配置不一致: $project_active / $configured_active"
  fi
  if [[ "$project_planned" != "$configured_planned" ]]; then
    report_failure "project.json planned language 与运行配置不一致: $project_planned / $configured_planned"
  fi
  if ((project_active_count != ${#ACTIVE_LANGUAGES[@]})); then
    report_failure "project.json active_language_count 与 active language 集合不一致"
  fi

  printf 'active languages: %s\n' "$configured_active"
}

check_audit_contract() {
  if [[ ! -f harness/README.md ]]; then
    report_failure "缺少 harness 层契约: harness/README.md"
  fi

  if ! python3 <<'PY'
import json

with open("project.json", encoding="utf-8") as project_file:
    project = json.load(project_file)

if project.get("architecture") != "language-concept-harness":
    raise SystemExit("project.json 未声明 language-concept-harness 三层结构")

if project.get("phase") == "nine-language-semantic-audit":
    if project.get("content_review_complete") is not False:
        raise SystemExit("语义审计期间 content_review_complete 必须为 false")
    if project.get("concept_curriculum_complete") is not False:
        raise SystemExit("语义审计期间 concept_curriculum_complete 必须为 false")
    for stale_key in ("reviewed_topic_count", "reviewed_language_implementation_count"):
        if stale_key in project:
            raise SystemExit(f"语义审计期间不得保留 {stale_key}")

harness = project.get("layers", {}).get("harness_and_integration", {})
if harness.get("counts_toward_language_curriculum") is not False:
    raise SystemExit("harness 不得计入语言课程完成度")
PY
  then
    report_failure "project.json 未满足语义审计与 harness 分层契约"
  fi
}

check_test_path() {
  local language="$1"
  local extension="$2"
  local path="$3"

  case "$language:$path" in
    python:languages/python/language/test_[0-9][0-9][0-9]_*.py)
      ;;
    python:languages/python/builtins/test_[0-9][0-9][0-9]_*.py)
      ;;
    python:languages/python/stdlib/*/test_[0-9][0-9][0-9]_*.py)
      ;;
    cpp:languages/cpp/language/test_[0-9][0-9][0-9]_*.cpp)
      ;;
    cpp:languages/cpp/standard_library/*/test_[0-9][0-9][0-9]_*.cpp)
      ;;
    nodejs:languages/nodejs/language/test_[0-9][0-9][0-9]_*.mjs)
      ;;
    nodejs:languages/nodejs/node_core/*/test_[0-9][0-9][0-9]_*.mjs)
      ;;
    nodejs:languages/nodejs/npm_and_package_workflows/test_[0-9][0-9][0-9]_*.mjs)
      ;;
    go:languages/go/language/*/test_[0-9][0-9][0-9]_*_test.go)
      ;;
    go:languages/go/standard_library/*/test_[0-9][0-9][0-9]_*_test.go)
      ;;
    go:languages/go/tooling_and_runtime/*/test_[0-9][0-9][0-9]_*_test.go)
      ;;
    rust:languages/rust/tests/language/*/test_[0-9][0-9][0-9]_*.rs)
      ;;
    rust:languages/rust/tests/standard_library/*/test_[0-9][0-9][0-9]_*.rs)
      ;;
    rust:languages/rust/tests/tooling_and_runtime/*/test_[0-9][0-9][0-9]_*.rs)
      ;;
    julia:languages/julia/language/*/test_[0-9][0-9][0-9]_*.jl)
      ;;
    julia:languages/julia/standard_library/*/test_[0-9][0-9][0-9]_*.jl)
      ;;
    julia:languages/julia/tooling_and_runtime/*/test_[0-9][0-9][0-9]_*.jl)
      ;;
    r:languages/r/language/*/test_[0-9][0-9][0-9]_*.R)
      ;;
    r:languages/r/standard_library/*/test_[0-9][0-9][0-9]_*.R)
      ;;
    r:languages/r/tooling_and_runtime/*/test_[0-9][0-9][0-9]_*.R)
      ;;
    lua:languages/lua/language/*/test_[0-9][0-9][0-9]_*.lua)
      ;;
    lua:languages/lua/standard_library/*/test_[0-9][0-9][0-9]_*.lua)
      ;;
    lua:languages/lua/tooling_and_runtime/*/test_[0-9][0-9][0-9]_*.lua)
      ;;
    ruby:languages/ruby/language/*/test_[0-9][0-9][0-9]_*.rb)
      ;;
    ruby:languages/ruby/standard_library/*/test_[0-9][0-9][0-9]_*.rb)
      ;;
    ruby:languages/ruby/tooling_and_runtime/*/test_[0-9][0-9][0-9]_*.rb)
      ;;
    *)
      report_failure "$language 测试位于未声明路径: $path"
      ;;
  esac

  if [[ "$path" != *".$extension" ]]; then
    report_failure "$language 测试扩展名错误: $path"
  fi
}

check_language() {
  local language="$1"
  local extension="$2"
  local test_pattern="${3:-test_[0-9][0-9][0-9]_*.${extension}}"
  local -a files=()
  local path
  local filename
  local number
  local number_index
  local minimum=1000
  local maximum=0
  local count=0
  local -a seen_paths=()

  while IFS= read -r -d '' path; do
    files+=("$path")
  done < <(
    find "languages/$language" \
      -type f \
      -name "$test_pattern" \
      -print0 | sort -z
  )

  if [[ ${#files[@]} -eq 0 ]]; then
    report_failure "$language 没有发现测试文件"
    return
  fi

  for path in "${files[@]}"; do
    check_test_path "$language" "$extension" "$path"
    filename="${path##*/}"
    number="${filename#test_}"
    number="${number%%_*}"
    number_index=$((10#$number))

    if [[ -n "${seen_paths[$number_index]:-}" ]]; then
      report_failure "$language 测试编号 $number 重复: ${seen_paths[$number_index]} 与 $path"
    else
      seen_paths[$number_index]="$path"
    fi

    if ! grep -q 'polyglot-covers:' "$path"; then
      report_failure "$language 测试缺少 polyglot-covers: $path"
    fi

    count=$((count + 1))
    if ((number_index < minimum)); then
      minimum=$number_index
    fi
    if ((number_index > maximum)); then
      maximum=$number_index
    fi
  done

  printf '%s: %d 个测试文件，编号 %03d–%03d（允许稳定空缺）\n' \
    "$language" "$count" "$minimum" "$maximum"
}

check_concept_language() {
  local family_slug="$1"
  local topic_slug="$2"
  local language="$3"
  local extension="$4"
  local language_directory="$5"
  local -a test_files=()
  local -a seen_numbers=()
  local path
  local filename
  local number
  local number_index
  local related_path
  local related_count
  local marker_count
  local child
  local child_name
  local test_pattern="test_[0-9][0-9]_*.${extension}"
  if [[ "$language" == go ]]; then
    test_pattern='test_[0-9][0-9]_*_test.go'
  fi

  while IFS= read -r -d '' path; do
    test_files+=("$path")
  done < <(
    find "$language_directory" \
      -maxdepth 1 \
      -type f \
      -name "$test_pattern" \
      -print0 | sort -z
  )

  if [[ ${#test_files[@]} -eq 0 ]]; then
    report_failure "$language_directory 至少需要一个 test_NN_name.${extension}"
    return
  fi

  while IFS= read -r -d '' path; do
    if [[ "$language" == go ]]; then
      if [[ ! "$path" =~ /test_[0-9]{2}_[a-z0-9_]+_test[.]go$ ]]; then
        report_failure "Go 概念测试必须使用 test_NN_name_test.go: $path"
      fi
    elif [[ ! "$path" =~ /test_[0-9]{2}_[a-z0-9_]+[.]${extension}$ ]]; then
      report_failure "概念测试必须使用 test_NN_name.${extension}: $path"
    fi
  done < <(
    find "$language_directory" \
      -maxdepth 1 \
      -type f \
      -name 'test_*' \
      -print0 | sort -z
  )

  for path in "${test_files[@]}"; do
    filename="${path##*/}"
    number="${filename#test_}"
    number="${number%%_*}"
    number_index=$((10#$number))
    if [[ -n "${seen_numbers[$number_index]:-}" ]]; then
      report_failure "$language_directory 测试编号 $number 重复"
    else
      seen_numbers[$number_index]="$path"
    fi

    marker_count=$(
      grep -Ec "polyglot-family:[[:space:]]*$family_slug[[:space:]]*$" "$path" || true
    )
    if ((marker_count != 1)); then
      report_failure "概念章节标记必须唯一且匹配目录: $path"
    fi

    marker_count=$(
      grep -Ec "polyglot-concept:[[:space:]]*$topic_slug[[:space:]]*$" "$path" || true
    )
    if ((marker_count != 1)); then
      report_failure "概念主题标记必须唯一且匹配目录: $path"
    fi

    related_count=0
    while IFS= read -r related_path; do
      related_count=$((related_count + 1))
      case "$related_path" in
        languages/"$language"/*)
          ;;
        *)
          report_failure "$path 的 polyglot-related 未指向 $language 主线"
          ;;
      esac
      if [[ ! -f "$related_path" ]]; then
        report_failure "$path 指向不存在的课程文件: $related_path"
      fi
    done < <(
      awk '
        /polyglot-related:[[:space:]]*/ {
          value = $0
          sub(/^.*polyglot-related:[[:space:]]*/, "", value)
          if (value ~ /\/$/) {
            prefix = value
          } else {
            print value
            prefix = ""
          }
          next
        }
        /polyglot-related\+:[[:space:]]*/ {
          value = $0
          sub(/^.*polyglot-related\+:[[:space:]]*/, "", value)
          print prefix value
          prefix = ""
        }
        END {
          if (prefix != "") {
            print prefix
          }
        }
      ' "$path"
    )

    if ((related_count == 0)); then
      report_failure "概念测试缺少 polyglot-related: $path"
    fi
  done

  for child in "$language_directory"/*; do
    if [[ ! -d "$child" ]]; then
      continue
    fi
    if git check-ignore -q "$child"; then
      continue
    fi
    child_name="${child##*/}"
    case "$child_name" in
      fixtures|support)
        ;;
      *)
        report_failure "$language_directory 包含未知辅助目录: $child_name"
        ;;
    esac
  done
}

check_concepts() {
  local family
  local family_name
  local family_number
  local family_index
  local family_slug
  local found_family=0
  local topic
  local topic_name
  local topic_number
  local topic_index
  local topic_slug
  local topic_count
  local language
  local extension
  local language_directory
  local language_count
  local child
  local child_name
  local -a seen_family_numbers=()
  local -a seen_topic_numbers=()

  for family in concepts/*; do
    if [[ ! -d "$family" ]]; then
      continue
    fi
    family_name="${family##*/}"
    case "$family_name" in
      src|tests)
        continue
        ;;
    esac
    found_family=1
    if [[ ! "$family_name" =~ ^[0-9]{2}_[a-z0-9_]+$ ]]; then
      report_failure "概念章节必须使用 NN_family 格式: $family_name"
      continue
    fi
    family_number="${family_name%%_*}"
    family_index=$((10#$family_number))
    family_slug="${family_name#*_}"

    if [[ -n "${seen_family_numbers[$family_index]:-}" ]]; then
      report_failure \
        "概念章节编号 $family_number 重复: ${seen_family_numbers[$family_index]} 与 $family_name"
    else
      seen_family_numbers[$family_index]="$family_name"
    fi

    seen_topic_numbers=()
    topic_count=0
    for topic in "$family"/*; do
      if [[ ! -d "$topic" ]]; then
        continue
      fi
      topic_count=$((topic_count + 1))
      topic_name="${topic##*/}"
      if [[ ! "$topic_name" =~ ^[0-9]{2}_[a-z0-9_]+$ ]]; then
        report_failure "$family_name 中的主题必须使用 NN_topic 格式: $topic_name"
        continue
      fi
      topic_number="${topic_name%%_*}"
      topic_index=$((10#$topic_number))
      topic_slug="${topic_name#*_}"

      if [[ -n "${seen_topic_numbers[$topic_index]:-}" ]]; then
        report_failure \
          "$family_name 主题编号 $topic_number 重复: ${seen_topic_numbers[$topic_index]} 与 $topic_name"
      else
        seen_topic_numbers[$topic_index]="$topic_name"
      fi

      language_count=0
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

        language_directory="$topic/$language"
        if [[ ! -d "$language_directory" ]]; then
          continue
        fi

        language_count=$((language_count + 1))
        check_concept_language \
          "$family_slug" \
          "$topic_slug" \
          "$language" \
          "$extension" \
          "$language_directory"
      done

      if ((language_count < 2)); then
        report_failure "$topic 至少需要两门 active language 形成真实对照，实际为 $language_count"
      fi

      for child in "$topic"/*; do
        if [[ ! -d "$child" ]]; then
          continue
        fi
        child_name="${child##*/}"
        case "$child_name" in
          python|cpp|nodejs|go|rust|julia|r|lua|ruby)
            ;;
          *)
            report_failure "$topic 包含未知语言目录: $child_name"
            ;;
        esac
      done
    done

    if ((topic_count == 0)); then
      report_failure "$family 没有发现 NN_topic 格式的横向主题"
    fi
  done

  if ((found_family == 0)); then
    report_failure "没有发现 NN_family 格式的概念章节"
  fi

}

check_go_workspace() {
  local required_file
  local workspace_json
  for required_file in harness/go/go.work harness/go/go.mod concepts/go.mod; do
    if [[ ! -f "$required_file" ]]; then
      report_failure "缺少 Go module/workspace 文件: $required_file"
    fi
  done

  if ! command -v go >/dev/null 2>&1; then
    report_failure "ohdev 中缺少 Go，无法验证 workspace"
    return
  fi
  if [[ "$(go env GOVERSION)" != go1.26.5 ]]; then
    report_failure "Go 工具链不是锁定的 go1.26.5"
  fi
  if ! workspace_json=$(GOWORK="$ROOT/harness/go/go.work" go work edit -json); then
    report_failure "harness/go/go.work 无法被 Go 工具链解析"
  else
    for required_file in "." "../../concepts"; do
      if ! grep -Fq "\"DiskPath\": \"$required_file\"" <<<"$workspace_json"; then
        report_failure "harness/go/go.work 缺少 workspace module: $required_file"
      fi
    done
  fi
  if ! (
    cd harness/go
    GOWORK=off go mod edit -json >/dev/null
  ); then
    report_failure "harness/go/go.mod 无法被 Go 工具链解析"
  fi
  if ! (
    cd concepts
    go mod edit -json >/dev/null
  ); then
    report_failure "concepts/go.mod 无法被 Go 工具链解析"
  fi

  local unformatted
  unformatted=$(
    find languages/go concepts harness/go \
      -type f \
      -name '*.go' \
      -print0 | xargs -0 gofmt -l
  )
  if [[ -n "$unformatted" ]]; then
    report_failure "Go 文件未通过 gofmt: $unformatted"
  fi
}

check_rust_workspaces() {
  local required_file
  local metadata
  local path
  local relative_path
  local directory_path
  local file_name
  local domain
  local domain_name
  local domain_number
  local domain_index
  local -a seen_domains=()
  for required_file in \
    Cargo.toml \
    Cargo.lock \
    harness/rust/runner/Cargo.toml \
    harness/rust/runner/build.rs \
    harness/rust/runner/tests/course.rs \
    harness/rust/runner/tests/harness.rs \
    harness/rust/runner/src/lib.rs \
    harness/rust/runner/src/bin/course_probe.rs \
    concepts/Cargo.toml \
    concepts/Cargo.lock \
    concepts/build.rs \
    concepts/tests/concepts.rs; do
    if [[ ! -f "$required_file" ]]; then
      report_failure "缺少 Rust Cargo workspace 文件: $required_file"
    fi
  done

  for required_file in rustc cargo rustfmt; do
    if ! command -v "$required_file" >/dev/null 2>&1; then
      report_failure "ohdev 中缺少 Rust 工具: $required_file"
      return
    fi
  done
  if [[ "$(rustc --version | awk '{print $2}')" != 1.97.1 ]]; then
    report_failure "rustc 不是锁定的 1.97.1"
  fi
  if [[ "$(cargo --version | awk '{print $2}')" != 1.97.1 ]]; then
    report_failure "Cargo 不是锁定的 1.97.1"
  fi
  if ! cargo clippy --version >/dev/null; then
    report_failure "ohdev 中缺少 Clippy"
  fi

  while IFS= read -r -d '' domain; do
    domain_name="${domain##*/}"
    domain_number="${domain_name%%_*}"
    domain_index=$((10#$domain_number))
    if [[ -n "${seen_domains[$domain_index]:-}" ]]; then
      report_failure "Rust 问题域编号 $domain_number 重复: ${seen_domains[$domain_index]} 与 $domain"
    else
      seen_domains[$domain_index]="$domain"
    fi
  done < <(
    find \
      languages/rust/tests/language \
      languages/rust/tests/standard_library \
      languages/rust/tests/tooling_and_runtime \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name '[0-9][0-9]_*' \
      -print0 | sort -z
  )
  if ! metadata=$(cargo metadata --manifest-path Cargo.toml --no-deps --format-version 1); then
    report_failure "根 Cargo.toml 无法被 Cargo 解析"
  elif [[ "$metadata" != *'"name":"polyglot-rust-harness"'* ]]; then
    report_failure "根 Cargo workspace 缺少 harness/rust/runner package"
  fi
  if ! metadata=$(
    cargo metadata --manifest-path concepts/Cargo.toml --no-deps --format-version 1
  ); then
    report_failure "concepts/Cargo.toml 无法被 Cargo 解析"
  elif [[ "$metadata" != *'"name":"polyglot-rust-concepts"'* ]]; then
    report_failure "concepts Cargo workspace 缺少横向 package"
  fi

  if ! cargo fmt --manifest-path Cargo.toml --all -- --check; then
    report_failure "Rust 纵向课程文件未通过 rustfmt"
  fi
  if ! cargo fmt --manifest-path concepts/Cargo.toml --all -- --check; then
    report_failure "Rust 横向概念文件未通过 rustfmt"
  fi

  if ! grep -Fq 'languages/rust' harness/rust/runner/build.rs || \
    ! grep -Fq 'test_' harness/rust/runner/build.rs; then
    report_failure "Rust harness build.rs 未按稳定 test_NNN 前缀发现纵向课程"
  fi
  if ! grep -Fq 'rust' concepts/build.rs || ! grep -Fq 'test_' concepts/build.rs; then
    report_failure "concepts/build.rs 未按实际 Rust 局部文件生成横向聚合入口"
  fi
}

check_julia_projects() {
  local required_file
  local actual_version
  local domain
  local domain_name
  local domain_number
  local domain_index
  local -a seen_domains=()

  for required_file in \
    harness/julia/fixture/PolyglotJuliaHarnessFixture/Project.toml \
    harness/julia/fixture/PolyglotJuliaHarnessFixture/src/PolyglotJuliaHarnessFixture.jl \
    harness/julia/tests/test_process_isolation.jl \
    harness/julia/tests/test_runtime_and_project_contract.jl \
    concepts/Project.toml; do
    if [[ ! -f "$required_file" ]]; then
      report_failure "缺少 Julia 项目文件: $required_file"
    fi
  done

  if ! command -v julia >/dev/null 2>&1; then
    report_failure "ohdev 中缺少 Julia，无法验证项目"
    return
  fi

  actual_version=$(
    JULIA_DEPOT_PATH=/tmp/polyglot-julia-check-depot \
      JULIA_LOAD_PATH='@:@stdlib' \
      julia --startup-file=no --history-file=no --project=@stdlib -e 'print(VERSION)'
  )
  if [[ "$actual_version" != 1.12.6 ]]; then
    report_failure "Julia 工具链不是锁定的 1.12.6，实际为 $actual_version"
  fi

  if ! JULIA_DEPOT_PATH=/tmp/polyglot-julia-check-depot \
    JULIA_LOAD_PATH='@:@stdlib' \
    julia \
      --startup-file=no \
      --history-file=no \
      --project=@stdlib \
      --depwarn=error \
      --check-bounds=yes \
      -e '
        using TOML
        for path in ARGS
            project = TOML.parsefile(path)
            get(get(project, "compat", Dict()), "julia", nothing) == "1.12.6" ||
                error("$path 必须精确锁定 julia = 1.12.6")
            isempty(get(project, "deps", Dict())) ||
                error("$path 的普通测试不得引入第三方 dependency")
        end
      ' harness/julia/fixture/PolyglotJuliaHarnessFixture/Project.toml \
        concepts/Project.toml; then
    report_failure "Julia Project.toml 无法解析或不满足版本、依赖约束"
  fi

  while IFS= read -r -d '' domain; do
    domain_name="${domain##*/}"
    domain_number="${domain_name%%_*}"
    domain_index=$((10#$domain_number))
    if [[ -n "${seen_domains[$domain_index]:-}" ]]; then
      report_failure "Julia 问题域编号 $domain_number 重复: ${seen_domains[$domain_index]} 与 $domain"
    else
      seen_domains[$domain_index]="$domain"
    fi
  done < <(
    find \
      languages/julia/language \
      languages/julia/standard_library \
      languages/julia/tooling_and_runtime \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name '[0-9][0-9]_*' \
      -print0 | sort -z
  )
}

check_r_projects() {
  local required_file
  local actual_version
  local domain
  local domain_name
  local domain_number
  local domain_index
  local state_probe
  local state_output
  local -a seen_domains=()

  for required_file in \
    harness/r/support/run_test.R \
    harness/r/support/package_helpers.R \
    harness/r/support/native_helpers.R \
    harness/r/package_fixture/polyglotrfixture/DESCRIPTION \
    harness/r/package_fixture/polyglotrfixture/NAMESPACE \
    harness/r/package_fixture/polyglotrfixture/R/functions.R \
    harness/r/package_fixture/polyglotrfixture/src/polyglotrfixture.c \
    harness/r/package_fixture/polyglotrfixture/tests/basic.R \
    harness/r/native/polyglot_native.c \
    harness/r/tests/test_runtime_contract.R \
    harness/r/tests/test_process_state_cleanup.R \
    harness/r/tests/test_package_workflow.R \
    harness/r/tests/test_native_build.R; do
    if [[ ! -f "$required_file" ]]; then
      report_failure "缺少 R runner、package 或 native fixture 文件: $required_file"
    fi
  done

  if ! command -v R >/dev/null 2>&1 || ! command -v Rscript >/dev/null 2>&1; then
    report_failure "ohdev 中缺少 R/Rscript，无法验证 R 工程"
    return
  fi

  actual_version="$(Rscript --vanilla -e 'cat(as.character(getRversion()))')"
  if [[ "$actual_version" != 4.6.1 ]]; then
    report_failure "R 工具链不是锁定的 4.6.1，实际为 $actual_version"
  fi

  if ! Rscript --vanilla -e '
    description <- read.dcf("harness/r/package_fixture/polyglotrfixture/DESCRIPTION")
    stopifnot(
      identical(unname(description[1L, "Package"]), "polyglotrfixture"),
      identical(unname(description[1L, "Version"]), "0.1.0"),
      identical(unname(description[1L, "NeedsCompilation"]), "yes")
    )
    namespace <- readLines(
      "harness/r/package_fixture/polyglotrfixture/NAMESPACE",
      warn = FALSE
    )
    stopifnot(
      any(grepl("useDynLib(polyglotrfixture", namespace, fixed = TRUE)),
      any(grepl("S3method(print, polyglot_label)", namespace, fixed = TRUE))
    )
  '; then
    report_failure "R package fixture 无法解析或缺少 namespace/native 注册"
  fi

  while IFS= read -r -d '' domain; do
    domain_name="${domain##*/}"
    domain_number="${domain_name%%_*}"
    domain_index=$((10#$domain_number))
    if [[ -n "${seen_domains[$domain_index]:-}" ]]; then
      report_failure "R 问题域编号 $domain_number 重复: ${seen_domains[$domain_index]} 与 $domain"
    else
      seen_domains[$domain_index]="$domain"
    fi
  done < <(
    find \
      languages/r/language \
      languages/r/standard_library \
      languages/r/tooling_and_runtime \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name '[0-9][0-9]_*' \
      -print0 | sort -z
  )
  for required_file in R_LIBS_USER R_USER TMPDIR R_ENVIRON_USER R_PROFILE_USER \
    Rscript --vanilla; do
    if ! grep -Fq -- "$required_file" tools/run-in-container.sh; then
      report_failure "R runner 缺少隔离设置: $required_file"
    fi
  done
  for required_file in options environment working_directory locale library_paths \
    search_path connections output_sinks message_sinks devices random_seed; do
    if ! grep -Fq "$required_file" harness/r/support/run_test.R; then
      report_failure "R 状态隔离器缺少快照维度: $required_file"
    fi
  done

  state_probe="$(mktemp /tmp/polyglot-r-state-probe.XXXXXX.R)"
  printf '%s\n' 'options(polyglot_state_probe = TRUE)' >"$state_probe"
  if state_output=$(
    R_LIBS_USER=/tmp/polyglot-r-state-library \
      R_USER=/tmp/polyglot-r-state-user \
      TMPDIR=/tmp \
      R_ENVIRON_USER=/dev/null \
      R_PROFILE_USER=/dev/null \
      Rscript --vanilla harness/r/support/run_test.R "$state_probe" 2>&1
  ); then
    report_failure "R 状态隔离器未拒绝 option 泄漏"
  elif [[ "$state_output" != *"test leaked process state: options"* ]]; then
    report_failure "R 状态隔离器泄漏探针返回了非预期诊断"
  fi
  rm -f "$state_probe"
}

check_lua_projects() {
  local required_file
  local actual_lua_version
  local actual_luac_version
  local domain
  local domain_name
  local domain_number
  local domain_index
  local build_root
  local c_case
  local -a seen_domains=()

  for required_file in \
    harness/lua/support/assertions.lua \
    harness/lua/support/c_api.lua \
    languages/lua/fixtures/modules/course_sample.lua \
    harness/lua/c_api/Makefile \
    harness/lua/c_api/polyglot_lua_host.c \
    harness/lua/c_api/polyglot_native.c \
    harness/lua/tests/test_environment_isolation.lua \
    harness/lua/tests/test_native_build.lua \
    harness/lua/tests/test_runtime_contract.lua; do
    if [[ ! -f "$required_file" ]]; then
      report_failure "缺少 Lua runner、module 或 C API 工程文件: $required_file"
    fi
  done

  for required_file in lua luac cc make; do
    if ! command -v "$required_file" >/dev/null 2>&1; then
      report_failure "ohdev 中缺少 Lua 工具链命令: $required_file"
      return
    fi
  done

  actual_lua_version="$(lua -E -v 2>&1 | awk '{print $2}')"
  actual_luac_version="$(luac -v 2>&1 | awk '{print $2}')"
  if [[ "$actual_lua_version" != 5.5.0 ]]; then
    report_failure "Lua 解释器不是锁定的 5.5.0，实际为 $actual_lua_version"
  fi
  if [[ "$actual_luac_version" != 5.5.0 ]]; then
    report_failure "luac 不是锁定的 5.5.0，实际为 $actual_luac_version"
  fi
  if [[ ! -f /opt/polyglot/lua-5.5.0/include/lua.h ]] || \
    [[ ! -f /opt/polyglot/lua-5.5.0/lib/liblua.a ]]; then
    report_failure "Lua 5.5.0 头文件或 liblua.a 不完整"
  elif ! grep -Fq '#define LUA_VERSION_RELEASE_NUM' \
    /opt/polyglot/lua-5.5.0/include/lua.h; then
    report_failure "Lua 头文件缺少 release 版本宏"
  fi

  for required_file in \
    '57ccc32bbbd005cab75bcc52444052535af691789dba2b9016d5c50640d68b3d'; do
    if ! grep -Fq "$required_file" sources.lock || \
      ! grep -Fq "$required_file" tools/bootstrap-language-toolchains-in-container.sh; then
      report_failure "Lua source lock 或 bootstrap 缺少锁定值: $required_file"
    fi
  done
  if ! grep -Fq 'https://www.lua.org/ftp/lua-5.5.0.tar.gz' sources.lock || \
    ! grep -Fq 'https://www.lua.org/ftp/' \
      tools/bootstrap-language-toolchains-in-container.sh; then
    report_failure "Lua source lock 或 bootstrap 缺少官方归档 URL"
  fi

  while IFS= read -r -d '' domain; do
    domain_name="${domain##*/}"
    domain_number="${domain_name%%_*}"
    domain_index=$((10#$domain_number))
    if [[ -n "${seen_domains[$domain_index]:-}" ]]; then
      report_failure "Lua 问题域编号 $domain_number 重复: ${seen_domains[$domain_index]} 与 $domain"
    else
      seen_domains[$domain_index]="$domain"
    fi
  done < <(
    find \
      languages/lua/language \
      languages/lua/standard_library \
      languages/lua/tooling_and_runtime \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name '[0-9][0-9]_*' \
      -print0 | sort -z
  )
  for required_file in \
    'function assertions.equal' \
    'function assertions.same' \
    'function assertions.truth' \
    'function assertions.raises' \
    'function assertions.with_cleanup' \
    'function assertions.done'; do
    if ! grep -Fq "$required_file" harness/lua/support/assertions.lua; then
      report_failure "Lua 最小断言库缺少能力: $required_file"
    fi
  done

  for required_file in \
    LUA_INIT LUA_INIT_5_5 LUA_PATH LUA_PATH_5_5 LUA_CPATH LUA_CPATH_5_5 \
    '-E' POLYGLOT_LUA_TEST_TMP POLYGLOT_LUA_C_API_HOST; do
    if ! grep -Fq -- "$required_file" tools/run-in-container.sh; then
      report_failure "Lua runner 缺少环境隔离设置: $required_file"
    fi
  done
  for required_file in \
    '-std=c11' '-Wall' '-Wextra' '-Wpedantic' '-Werror' \
    polyglot_lua_host polyglot_native.so; do
    if ! grep -Fq -- "$required_file" harness/lua/c_api/Makefile; then
      report_failure "Lua C API 工程缺少严格构建设置: $required_file"
    fi
  done

  build_root="$(mktemp -d /tmp/polyglot-lua-structure.XXXXXX)"
  if ! make \
    --no-print-directory \
    -C harness/lua/c_api \
    LUA_HOME=/opt/polyglot/lua-5.5.0 \
    BUILD_DIR="$build_root" \
    all >/dev/null; then
    report_failure "Lua C API 工程无法严格编译"
  else
    for c_case in \
      state selected-libraries stack tables-registry closures protected \
      continuation userdata allocator-warning hook dump-load state-isolation \
      structured auxiliary external-string version-gc; do
      if ! "$build_root/polyglot_lua_host" "$c_case" >/dev/null; then
        report_failure "Lua C API 宿主用例失败: $c_case"
      fi
    done
    if ! POLYGLOT_LUA_CPATH="$build_root/?.so" \
      lua -E -e '
        package.cpath = assert(os.getenv("POLYGLOT_LUA_CPATH"))
        local native = require("polyglot_native")
        assert(native.release == "Lua 5.5.0")
        assert(native.add(20, 22) == 42)
      '; then
      report_failure "Lua C module 无法通过受控 module path 加载"
    fi
  fi

  if ! lua -E -e '
    _G.polyglot_state_probe = true
    package.loaded.polyglot_state_probe = true
    debug.sethook(function() end, "", 1)
    collectgarbage("generational")
    math.randomseed(1, 2)
    local file = assert(io.tmpfile())
    io.output(file)
  ' || ! lua -E -e '
    assert(rawget(_G, "polyglot_state_probe") == nil)
    assert(package.loaded.polyglot_state_probe == nil)
    assert(debug.gethook() == nil)
    assert(io.type(io.output()) == "file")
  '; then
    report_failure "Lua 独立进程状态隔离探针失败"
  fi
  rm -rf "$build_root"
}

check_ruby_projects() {
  local required_file
  local actual_version
  local actual_engine
  local domain
  local domain_name
  local domain_number
  local domain_index
  local build_root
  local -a seen_domains=()

  for required_file in \
    harness/ruby/support/assertions.rb \
    harness/ruby/support/helpers.rb \
    harness/ruby/support/package_helpers.rb \
    harness/ruby/gem_fixture/polyglot_ruby_fixture/polyglot_ruby_fixture.gemspec \
    harness/ruby/gem_fixture/polyglot_ruby_fixture/lib/polyglot_ruby_fixture.rb \
    harness/ruby/gem_fixture/polyglot_ruby_fixture/lib/polyglot_ruby_fixture/version.rb \
    harness/ruby/gem_fixture/polyglot_ruby_fixture/exe/polyglot-ruby-fixture \
    harness/ruby/gem_fixture/polyglot_ruby_fixture/Rakefile \
    harness/ruby/c_extension/extconf.rb \
    harness/ruby/c_extension/polyglot_native.c \
    harness/ruby/c_extension/Rakefile; do
    if [[ ! -f "$required_file" ]]; then
      report_failure "缺少 Ruby runner、gem fixture 或 C Extension 文件: $required_file"
    fi
  done

  for required_file in ruby gem bundle rake cc make; do
    if ! command -v "$required_file" >/dev/null 2>&1; then
      report_failure "ohdev 中缺少 Ruby 工具链命令: $required_file"
      return
    fi
  done

  actual_version="$(ruby --disable-gems -e 'print RUBY_VERSION')"
  actual_engine="$(ruby --disable-gems -e 'print RUBY_ENGINE')"
  if [[ "$actual_version" != 4.0.6 ]] || [[ "$actual_engine" != ruby ]]; then
    report_failure "Ruby 工具链需要 CRuby 4.0.6，实际为 $actual_engine $actual_version"
  fi
  if [[ ! -f /opt/polyglot/ruby-4.0.6/include/ruby-4.0.0/ruby.h ]]; then
    report_failure "Ruby 4.0.6 公共 C Extension 头文件不完整"
  fi

  for required_file in \
    '837d299e8f7ddf2be31a229a7a7e019d354979825117989acb3b32b1a9be262a'; do
    if ! grep -Fq "$required_file" sources.lock || \
      ! grep -Fq "$required_file" tools/bootstrap-language-toolchains-in-container.sh; then
      report_failure "Ruby source lock 或 bootstrap 缺少锁定值: $required_file"
    fi
  done
  if ! grep -Fq 'https://cache.ruby-lang.org/pub/ruby/4.0/ruby-4.0.6.tar.gz' sources.lock || \
    ! grep -Fq 'https://cache.ruby-lang.org/pub/ruby/4.0/' \
      tools/bootstrap-language-toolchains-in-container.sh; then
    report_failure "Ruby source lock 或 bootstrap 缺少官方归档 URL"
  fi

  while IFS= read -r -d '' domain; do
    domain_name="${domain##*/}"
    domain_number="${domain_name%%_*}"
    domain_index=$((10#$domain_number))
    if [[ -n "${seen_domains[$domain_index]:-}" ]]; then
      report_failure "Ruby 问题域编号 $domain_number 重复: ${seen_domains[$domain_index]} 与 $domain"
    else
      seen_domains[$domain_index]="$domain"
    fi
  done < <(
    find \
      languages/ruby/language \
      languages/ruby/standard_library \
      languages/ruby/tooling_and_runtime \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name '[0-9][0-9]_*' \
      -print0 | sort -z
  )
  for required_file in \
    RUBYOPT RUBYLIB GEM_HOME GEM_PATH GEMRC BUNDLE_GEMFILE BUNDLE_PATH \
    BUNDLE_APP_CONFIG HOME TMPDIR POLYGLOT_RUBY_TEST_TMP POLYGLOT_RUBY_EXTENSION_DIR; do
    if ! grep -Fq -- "$required_file" tools/run-in-container.sh; then
      report_failure "Ruby runner 缺少环境隔离设置: $required_file"
    fi
  done
  for required_file in '-std=c11' '-Wall' '-Wextra' '-Werror'; do
    if ! grep -Fq -- "$required_file" harness/ruby/c_extension/extconf.rb; then
      report_failure "Ruby C Extension 缺少严格构建设置: $required_file"
    fi
  done
  if grep -Eq '#include[[:space:]]+[<\"]ruby/internal/' \
    harness/ruby/c_extension/polyglot_native.c; then
    report_failure "Ruby C Extension 不得依赖 CRuby private/internal 头文件"
  fi

  if ! ruby -rrubygems -e '
    specification = Gem::Specification.load(
      "harness/ruby/gem_fixture/polyglot_ruby_fixture/polyglot_ruby_fixture.gemspec"
    )
    abort "invalid gem fixture" unless
      specification&.name == "polyglot_ruby_fixture" &&
      specification.version.to_s == "0.1.0" &&
      specification.executables == ["polyglot-ruby-fixture"]
  '; then
    report_failure "Ruby gem fixture 无法由锁定 RubyGems 解析"
  fi

  build_root="$(mktemp -d /tmp/polyglot-ruby-structure.XXXXXX)"
  if ! (
    cd "$build_root"
    ruby "$ROOT/harness/ruby/c_extension/extconf.rb" >/dev/null
    make >/dev/null
  ); then
    report_failure "Ruby C Extension 无法使用公共头文件严格编译"
  elif ! ruby -I "$build_root" -rpolyglot_native -e '
    abort "invalid native release" unless PolyglotNative::RELEASE == "CRuby 4.0.6"
    abort "invalid native result" unless PolyglotNative.add(20, 22) == 42
  '; then
    report_failure "Ruby C Extension 无法从受控 build path 加载"
  fi
  rm -rf "$build_root"

  if ! ruby -e '
    ENV["POLYGLOT_RUBY_STATE_PROBE"] = "child"
    Object.const_set(:PolyglotRubyStateProbe, true)
  ' || ! ruby -e '
    abort if ENV.key?("POLYGLOT_RUBY_STATE_PROBE")
    abort if Object.const_defined?(:PolyglotRubyStateProbe, false)
  '; then
    report_failure "Ruby 独立解释器进程状态隔离探针失败"
  fi
}

check_unicode_line_lengths() {
  local -a checked_files=()
  local path
  while IFS= read -r -d '' path; do
    if [[ -f "$path" ]]; then
      checked_files+=("$path")
    fi
  done < <(git ls-files --cached --others --exclude-standard -z)

  if ! POLYGLOT_MAX_LINE_LENGTH="$MAX_LINE_LENGTH" perl -Mutf8 -e '
    use strict;
    use warnings;
    use open qw(:std :encoding(UTF-8));

    my $limit = $ENV{POLYGLOT_MAX_LINE_LENGTH};
    my $failed = 0;
    for my $path (@ARGV) {
      open my $file, "<:encoding(UTF-8)", $path
        or die "无法读取 $path: $!\n";
      my $line_number = 0;
      while (my $line = <$file>) {
        $line_number += 1;
        $line =~ s/\r?\n\z//;
        my $length = length($line);
        if ($length > $limit) {
          print STDERR "$path:$line_number: $length 个 Unicode 字符，限制为 $limit\n";
          $failed = 1;
        }
      }
      close $file;
    }
    exit $failed;
  ' "${checked_files[@]}"; then
    report_failure "存在超过 $MAX_LINE_LENGTH 个 Unicode 字符的行"
  fi
}

check_active_language_state
check_audit_contract
for active_language in "${ACTIVE_LANGUAGES[@]}"; do
  case "$active_language" in
    python)
      check_language python py
      ;;
    cpp)
      check_language cpp cpp
      ;;
    nodejs)
      check_language nodejs mjs
      ;;
    go)
      check_language go go 'test_[0-9][0-9][0-9]_*_test.go'
      ;;
    rust)
      check_language rust rs
      ;;
    julia)
      check_language julia jl
      ;;
    r)
      check_language r R
      ;;
    lua)
      check_language lua lua
      ;;
    ruby)
      check_language ruby rb
      ;;
    *)
      report_failure "缺少 active language 结构检查实现: $active_language"
      ;;
  esac
done
check_concepts
check_go_workspace
check_rust_workspaces
check_julia_projects
check_r_projects
check_lua_projects
check_ruby_projects
check_unicode_line_lengths

if ((failure_count > 0)); then
  printf '结构检查共发现 %d 类问题。\n' "$failure_count" >&2
  exit 1
fi

printf '语言与概念路径、唯一编号、结构标记、引用完整性和 Unicode %d 字符行宽检查通过。\n' \
  "$MAX_LINE_LENGTH"
printf '注意: 结构门禁不判断课程完整性、断言语义或 polyglot-related 的教学相关性。\n'
