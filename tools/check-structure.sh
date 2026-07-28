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
  local expected_active="python cpp nodejs go rust"
  local configured_active="${ACTIVE_LANGUAGES[*]}"
  local configured_planned="${PLANNED_LANGUAGES[*]}"
  local project_active
  local project_active_count
  local project_planned

  if [[ "$configured_active" != "$expected_active" ]]; then
    report_failure "稳定 active language 集合错误: $configured_active"
  fi

  project_active=$(project_language_ids verified)
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
    if ((number_index > maximum)); then
      maximum=$number_index
    fi
  done

  local expected
  for ((expected = 1; expected <= maximum; expected += 1)); do
    printf -v number '%03d' "$expected"
    if [[ -z "${seen_paths[$expected]:-}" ]]; then
      report_failure "$language 缺少连续测试编号 $number"
    fi
  done

  if ((count != maximum)); then
    report_failure "$language 文件数 $count 与最大连续编号 $maximum 不一致"
  fi

  printf '%s: %d 个测试文件，编号 001–%03d\n' "$language" "$count" "$maximum"
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
  local maximum=0
  local test_count=0
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
    test_count=$((test_count + 1))

    if [[ -n "${seen_numbers[$number_index]:-}" ]]; then
      report_failure "$language_directory 测试编号 $number 重复"
    else
      seen_numbers[$number_index]="$path"
    fi
    if ((number_index > maximum)); then
      maximum=$number_index
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

  local expected
  for ((expected = 1; expected <= maximum; expected += 1)); do
    printf -v number '%02d' "$expected"
    if [[ -z "${seen_numbers[$expected]:-}" ]]; then
      report_failure "$language_directory 缺少连续测试编号 $number"
    fi
  done

  if ((test_count != maximum)); then
    report_failure "$language_directory 文件数 $test_count 与最大编号 $maximum 不一致"
  fi

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
  local expected_family_index=1
  local found_family=0
  local topic
  local topic_name
  local topic_number
  local topic_index
  local topic_slug
  local expected_topic_index
  local topic_count
  local language
  local extension
  local language_directory
  local language_count
  local child
  local child_name

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

    if ((family_index != expected_family_index)); then
      printf -v family_number '%02d' "$expected_family_index"
      report_failure "概念章节编号不连续，期望 $family_number，实际为 $family_name"
      expected_family_index=$family_index
    fi
    expected_family_index=$((expected_family_index + 1))

    expected_topic_index=1
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

      if ((topic_index != expected_topic_index)); then
        printf -v topic_number '%02d' "$expected_topic_index"
        report_failure "$family_name 主题编号不连续，期望 $topic_number，实际为 $topic_name"
        expected_topic_index=$topic_index
      fi
      expected_topic_index=$((expected_topic_index + 1))

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
        esac

        language_directory="$topic/$language"
        if [[ ! -d "$language_directory" ]]; then
          report_failure "$topic 缺少 active language: $language"
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

      if ((language_count != ${#ACTIVE_LANGUAGES[@]})); then
        report_failure "$topic 需要 ${#ACTIVE_LANGUAGES[@]} 门 active language，实际为 $language_count"
      fi

      local python_stems
      local go_stems
      local rust_stems
      python_stems=$(
        find "$topic/python" -maxdepth 1 -type f -name 'test_[0-9][0-9]_*.py' \
          -exec basename {} .py \; | sort
      )
      go_stems=$(
        find "$topic/go" -maxdepth 1 -type f -name 'test_[0-9][0-9]_*_test.go' \
          -exec basename {} _test.go \; | sort
      )
      rust_stems=$(
        find "$topic/rust" -maxdepth 1 -type f -name 'test_[0-9][0-9]_*.rs' \
          -exec basename {} .rs \; | sort
      )
      if [[ "$python_stems" != "$go_stems" ]]; then
        report_failure "$topic 的 Go 子问题文件没有镜像既有测试结构"
      fi
      if [[ "$python_stems" != "$rust_stems" ]]; then
        report_failure "$topic 的 Rust 子问题文件没有镜像既有测试结构"
      fi

      for child in "$topic"/*; do
        if [[ ! -d "$child" ]]; then
          continue
        fi
        child_name="${child##*/}"
        case "$child_name" in
          python|cpp|nodejs|go|rust)
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
  for required_file in go.work languages/go/go.mod concepts/go.mod; do
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
  if ! workspace_json=$(go work edit -json); then
    report_failure "go.work 无法被 Go 工具链解析"
  else
    for required_file in "./languages/go" "./concepts"; do
      if ! grep -Fq "\"DiskPath\": \"$required_file\"" <<<"$workspace_json"; then
        report_failure "go.work 缺少 workspace module: $required_file"
      fi
    done
  fi
  if ! (
    cd languages/go
    go mod edit -json >/dev/null
  ); then
    report_failure "languages/go/go.mod 无法被 Go 工具链解析"
  fi
  if ! (
    cd concepts
    go mod edit -json >/dev/null
  ); then
    report_failure "concepts/go.mod 无法被 Go 工具链解析"
  fi

  local unformatted
  unformatted=$(
    find languages/go concepts \
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
  local domain_count=0
  local expected_domain
  local rust_test_count
  local -a seen_domains=()
  for required_file in \
    Cargo.toml \
    Cargo.lock \
    languages/rust/Cargo.toml \
    languages/rust/tests/course.rs \
    concepts/Cargo.toml \
    concepts/Cargo.lock \
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
    domain_count=$((domain_count + 1))
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
  if ((domain_count != 16)); then
    report_failure "Rust 纵向课程需要 16 个问题域，实际为 $domain_count"
  fi
  for ((expected_domain = 1; expected_domain <= 16; expected_domain += 1)); do
    if [[ -z "${seen_domains[$expected_domain]:-}" ]]; then
      printf -v domain_number '%02d' "$expected_domain"
      report_failure "Rust 纵向课程缺少问题域 $domain_number"
    fi
  done
  rust_test_count=$(
    find languages/rust/tests -type f -name 'test_[0-9][0-9][0-9]_*.rs' -print | wc -l
  )
  if ((rust_test_count < 120)); then
    report_failure "Rust 纵向课程至少需要 120 个测试文件，实际为 $rust_test_count"
  fi

  if ! metadata=$(cargo metadata --manifest-path Cargo.toml --no-deps --format-version 1); then
    report_failure "根 Cargo.toml 无法被 Cargo 解析"
  elif [[ "$metadata" != *'"name":"polyglot-rust-course"'* ]]; then
    report_failure "根 Cargo workspace 缺少 languages/rust package"
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

  while IFS= read -r -d '' path; do
    relative_path="${path#languages/rust/tests/}"
    directory_path="${relative_path%/*}/"
    file_name="${relative_path##*/}"
    if ! grep -Fq "\"$directory_path\"" languages/rust/tests/course.rs || \
      ! grep -Fq "\"$file_name\"" languages/rust/tests/course.rs; then
      report_failure "Rust 纵向测试未接入 Cargo 聚合入口: $path"
    fi
  done < <(
    find languages/rust -type f -name 'test_[0-9][0-9][0-9]_*.rs' -print0 | sort -z
  )
  while IFS= read -r -d '' path; do
    relative_path="${path#concepts/}"
    directory_path="../${relative_path%/*}/"
    file_name="${relative_path##*/}"
    if ! grep -Fq "\"$directory_path\"" concepts/tests/concepts.rs || \
      ! grep -Fq "\"$file_name\"" concepts/tests/concepts.rs; then
      report_failure "Rust 横向测试未接入 Cargo 聚合入口: $path"
    fi
  done < <(
    find concepts -type f -path '*/rust/test_[0-9][0-9]_*.rs' -print0 | sort -z
  )
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
    *)
      report_failure "缺少 active language 结构检查实现: $active_language"
      ;;
  esac
done
check_concepts
check_go_workspace
check_rust_workspaces
check_unicode_line_lengths

if ((failure_count > 0)); then
  printf '结构检查共发现 %d 类问题。\n' "$failure_count" >&2
  exit 1
fi

printf '语言主线、概念章节与主题、关联标记、连续编号和 Unicode %d 字符行宽检查通过。\n' \
  "$MAX_LINE_LENGTH"
