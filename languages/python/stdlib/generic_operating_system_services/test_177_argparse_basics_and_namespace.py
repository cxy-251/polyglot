"""177｜``argparse`` 的声明式参数解析、类型转换与 ``Namespace``。

``ArgumentParser`` 把命令行 token 映射到由 ``add_argument`` 声明的目标属性；
``type`` 在 ``choices`` 校验前转换输入。option 名中的连字符默认会转成属性名中的
下划线。这里直接传入 token list，避免案例依赖 pytest 自身的 ``sys.argv``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.argparse.ArgumentParser python.argparse.add_argument
# polyglot-covers: python.argparse.parse_args python.argparse.Namespace
# polyglot-covers: python.argparse.positional python.argparse.optional
# polyglot-covers: python.argparse.type python.argparse.choices
# polyglot-covers: python.argparse.dest python.argparse.required-option
# polyglot-covers: python.argparse.option-equals-syntax python.argparse.short-option-attached-value
# polyglot-covers: python.argparse.short-option-cluster python.argparse.end-of-options
# polyglot-covers: python.argparse.negative-number-positional
# polyglot-covers: python.argparse.negative-number-option-ambiguity
# polyglot-covers: python.argparse.existing-namespace python.argparse.namespace-vars

import argparse


def test_parser_builds_a_typed_namespace_from_positionals_and_options():
    """type 的结果参与 choices；命令行字符串不会原样留在 Namespace 中。"""

    parser = argparse.ArgumentParser(prog="copy")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--retry-count", type=int, choices=range(1, 4), default=2)

    args = parser.parse_args(
        ["first.txt", "second.txt", "--output", "archive.zip", "--retry-count", "3"]
    )

    assert args == argparse.Namespace(
        sources=["first.txt", "second.txt"],
        output="archive.zip",
        retry_count=3,
    )
    assert vars(args)["retry_count"] == 3


def test_common_token_spellings_and_double_dash_are_not_shell_features():
    """这些形式由 argparse 解析；传 list 时并没有 shell 帮忙拆分。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("-I", dest="include_paths", action="append", default=[])
    parser.add_argument("--format", choices=("json", "text"))
    parser.add_argument("items", nargs="*")

    args = parser.parse_args(
        ["-vv", "-I/usr/include", "--format=json", "--", "--literal", "-3"]
    )

    assert args.verbose == 2
    assert args.include_paths == ["/usr/include"]
    assert args.format == "json"
    # ``--`` 自身不会进入结果；其后的 ``-`` 前缀 token 一律作为位置参数。
    assert args.items == ["--literal", "-3"]


def test_existing_namespace_keeps_defaults_but_explicit_tokens_still_win():
    """默认值只填补缺失属性；显式提供的 option 仍会覆盖已有属性。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--color", default="auto")
    parser.add_argument("--jobs", type=int, default="4")

    target = argparse.Namespace(color="always", marker="preserved")
    result = parser.parse_args([], namespace=target)

    assert result is target
    assert result.color == "always"
    assert result.jobs == 4
    assert result.marker == "preserved"

    parser.parse_args(["--color", "never"], namespace=target)
    assert target.color == "never"


def test_negative_numbers_are_positionals_until_a_similar_option_is_declared():
    """存在 ``-1`` option 时，负数 token 会进入 option 识别；``--`` 可消除歧义。"""

    numeric = argparse.ArgumentParser()
    numeric.add_argument("offset", type=int)
    assert numeric.parse_args(["-3"]).offset == -3

    ambiguous = argparse.ArgumentParser()
    ambiguous.add_argument("-1", dest="use_one", action="store_true")
    ambiguous.add_argument("offset", type=int)

    option = ambiguous.parse_args(["-1", "5"])
    positional = ambiguous.parse_args(["--", "-1"])

    assert option == argparse.Namespace(use_one=True, offset=5)
    assert positional == argparse.Namespace(use_one=False, offset=-1)
