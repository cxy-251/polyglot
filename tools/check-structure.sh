#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

readonly MAX_LINE_LENGTH=120
failure_count=0

report_failure() {
  printf '结构检查失败: %s\n' "$*" >&2
  failure_count=$((failure_count + 1))
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
      -name "test_[0-9][0-9][0-9]_*.${extension}" \
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

check_concepts() {
  local concept
  local concept_name
  local concept_number
  local concept_index
  local concept_slug
  local expected_index=1
  local found_concept=0
  local language
  local extension
  local language_directory
  local language_count
  local test_file
  local test_count
  local related_path
  local related_count
  local child
  local child_name

  for concept in concepts/*; do
    if [[ ! -d "$concept" ]]; then
      continue
    fi
    found_concept=1
    concept_name="${concept##*/}"
    if [[ ! "$concept_name" =~ ^[0-9]{3}_[a-z0-9_]+$ ]]; then
      report_failure "概念目录必须使用 NNN_name 格式: $concept_name"
      continue
    fi
    concept_number="${concept_name%%_*}"
    concept_index=$((10#$concept_number))
    concept_slug="${concept_name#*_}"

    if ((concept_index != expected_index)); then
      printf -v concept_number '%03d' "$expected_index"
      report_failure "概念目录编号不连续，期望 $concept_number，实际为 $concept_name"
      expected_index=$concept_index
    fi
    expected_index=$((expected_index + 1))

    language_count=0
    for language in python cpp nodejs; do
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
      esac

      language_directory="$concept/$language"
      if [[ ! -d "$language_directory" ]]; then
        continue
      fi

      test_count=$(
        find "$language_directory" \
          -maxdepth 1 \
          -type f \
          -name 'test_*' \
          -print | wc -l | tr -d ' '
      )
      test_file="$language_directory/test_${concept_slug}.${extension}"

      if ((test_count != 1)) || [[ ! -f "$test_file" ]]; then
        report_failure "$language_directory 必须只有 test_${concept_slug}.${extension}"
        continue
      fi

      language_count=$((language_count + 1))
      if ! grep -Eq "polyglot-concept:[[:space:]]*$concept_slug[[:space:]]*$" "$test_file"; then
        report_failure "概念测试标记不匹配: $test_file"
      fi

      related_count=0
      while IFS= read -r related_path; do
        related_count=$((related_count + 1))
        case "$related_path" in
          languages/"$language"/*)
            ;;
          *)
            report_failure "$test_file 的 polyglot-related 未指向 $language 主线"
            ;;
        esac
        if [[ ! -f "$related_path" ]]; then
          report_failure "$test_file 指向不存在的课程文件: $related_path"
        fi
      done < <(
        sed -n 's/^.*polyglot-related:[[:space:]]*//p' "$test_file"
      )
      if ((related_count == 0)); then
        report_failure "概念测试缺少 polyglot-related: $test_file"
      fi
    done

    if ((language_count < 2)); then
      report_failure "$concept 只有 $language_count 门语言，不能构成跨语言概念"
    fi

    for child in "$concept"/*; do
      if [[ ! -d "$child" ]]; then
        continue
      fi
      child_name="${child##*/}"
      case "$child_name" in
        python|cpp|nodejs)
          ;;
        *)
          report_failure "$concept 包含未知语言目录: $child_name"
          ;;
      esac
    done
  done

  if ((found_concept == 0)); then
    report_failure "没有发现 NNN_name 格式的共同概念目录"
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

check_language python py
check_language cpp cpp
check_language nodejs mjs
check_concepts
check_unicode_line_lengths

if ((failure_count > 0)); then
  printf '结构检查共发现 %d 类问题。\n' "$failure_count" >&2
  exit 1
fi

printf '语言主线、横向概念、关联标记、连续编号和 Unicode %d 字符行宽检查通过。\n' \
  "$MAX_LINE_LENGTH"
