"""181｜``argparse`` 的 partial parse、intermixed parse 与 ``@`` 参数文件。

``parse_known_args`` 适合把未知 token 转交给下一级，但仍受长 option 缩写规则影响。
``parse_intermixed_args`` 允许可选参数穿插在 ``nargs='*'`` 位置参数中。参数文件默认一行
对应一个 token；若需要 shell-like 引号或一行多参数，应覆盖转换 hook 并明确其语法。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.argparse.parse_known_args python.argparse.unknown-arguments
# polyglot-covers: python.argparse.parse_intermixed_args
# polyglot-covers: python.argparse.parse_known_intermixed_args
# polyglot-covers: python.argparse.intermixed-positional-options
# polyglot-covers: python.argparse.fromfile_prefix_chars
# polyglot-covers: python.argparse.argument-file-one-token-per-line
# polyglot-covers: python.argparse.convert_arg_line_to_args
# polyglot-covers: python.argparse.argument-file-custom-tokenization

import argparse
import shlex


class ShellLineArgumentParser(argparse.ArgumentParser):
    """把每行显式定义为 shlex 语法，并允许 ``#`` 注释。"""

    def convert_arg_line_to_args(self, arg_line):
        return shlex.split(arg_line, comments=True)


def test_parse_known_args_returns_unknown_tokens_without_rejecting_them():
    """已知参数照常类型转换，未知参数保持原顺序交给调用方。"""

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--jobs", type=int, default=1)

    args, unknown = parser.parse_known_args(
        ["--jobs", "4", "--plugin-color", "blue", "payload"]
    )

    assert args == argparse.Namespace(jobs=4)
    assert unknown == ["--plugin-color", "blue", "payload"]


def test_intermixed_parse_reopens_a_star_positional_after_an_option():
    """普通解析会把 option 后恢复的位置值留作 unknown；intermixed 会重新收集它们。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--format")
    parser.add_argument("command")
    parser.add_argument("values", nargs="*", type=int)
    tokens = ["sum", "1", "--format", "json", "2", "3"]

    regular, regular_unknown = parser.parse_known_args(tokens)
    intermixed = parser.parse_intermixed_args(tokens)

    assert regular.command == "sum"
    assert regular.values == [1]
    assert regular_unknown == ["2", "3"]
    assert intermixed == argparse.Namespace(format="json", command="sum", values=[1, 2, 3])


def test_known_intermixed_variant_preserves_unrecognized_options():
    """known 与 intermixed 可组合，用于既允许穿插又需要向下转交参数的场景。"""

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--format")
    parser.add_argument("values", nargs="*", type=int)

    args, unknown = parser.parse_known_intermixed_args(
        ["1", "--format", "json", "2", "--plugin-flag"]
    )

    assert args == argparse.Namespace(format="json", values=[1, 2])
    assert unknown == ["--plugin-flag"]


def test_default_argument_file_conversion_treats_each_line_as_one_token(tmp_path):
    """默认实现不按空白再次拆词，因此 option 及其值通常分别占一行。"""

    argument_file = tmp_path / "arguments.txt"
    argument_file.write_text("--mode\nfast\ninput file.txt\n", encoding="utf-8")

    parser = argparse.ArgumentParser(fromfile_prefix_chars="@")
    parser.add_argument("--mode")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args([f"@{argument_file}"])

    assert args.mode == "fast"
    assert args.files == ["input file.txt"]


def test_argument_file_hook_can_define_quoted_multi_token_lines(tmp_path):
    """自定义转换器的规则属于文件格式契约，不应暗中依赖平台 shell。"""

    argument_file = tmp_path / "shell-like.args"
    argument_file.write_text(
        '--name "Ada Lovelace"\n--tag alpha --tag beta # ignored\n',
        encoding="utf-8",
    )

    parser = ShellLineArgumentParser(fromfile_prefix_chars="@")
    parser.add_argument("--name")
    parser.add_argument("--tag", action="append")
    args = parser.parse_args([f"@{argument_file}"])

    assert args.name == "Ada Lovelace"
    assert args.tag == ["alpha", "beta"]
