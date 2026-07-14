"""178｜``argparse`` 内建 action、``nargs`` 结果形状与默认值语义。

action 决定重复 option 如何更新同一个目标；``nargs`` 不只控制消费多少 token，
也会改变结果是 scalar 还是 list。默认值的转换规则尤其容易忽略：只有字符串
默认值会经过 ``type``，已经是其他 Python 对象的默认值会原样保存。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.argparse.action-store python.argparse.action-store-const
# polyglot-covers: python.argparse.action-store-true python.argparse.action-store-false
# polyglot-covers: python.argparse.BooleanOptionalAction python.argparse.action-count
# polyglot-covers: python.argparse.action-append python.argparse.action-append-const
# polyglot-covers: python.argparse.action-extend python.argparse.append-default-prefix
# polyglot-covers: python.argparse.nargs-integer python.argparse.nargs-question
# polyglot-covers: python.argparse.nargs-star python.argparse.nargs-plus
# polyglot-covers: python.argparse.REMAINDER python.argparse.nargs-result-shape
# polyglot-covers: python.argparse.string-default-type-conversion
# polyglot-covers: python.argparse.non-string-default-not-converted python.argparse.SUPPRESS

import argparse


def test_constant_boolean_and_count_actions_encode_flag_semantics():
    """无值 flag 应用 action 表意，避免手工把字符串 ``"false"`` 当布尔值。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="store", default="normal")
    parser.add_argument("--fast", dest="mode", action="store_const", const="fast")
    parser.add_argument("--verbose", action="count", default=0)
    parser.add_argument("--color", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--feature", action="store_true")
    parser.add_argument("--no-cache", dest="cache", action="store_false", default=True)

    args = parser.parse_args(
        ["--fast", "--verbose", "--verbose", "--no-color", "--feature", "--no-cache"]
    )

    assert args.mode == "fast"
    assert args.verbose == 2
    assert args.color is False
    assert args.feature is True
    assert args.cache is False


def test_repeating_actions_accumulate_with_distinct_flattening_rules():
    """append 追加一个值，extend 展开一组值，append_const 追加预设常量。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", action="append", default=["base"])
    parser.add_argument("--include", action="extend", nargs="+")
    parser.add_argument("--debug-kind", dest="kinds", action="append_const", const="debug")
    parser.add_argument("--trace-kind", dest="kinds", action="append_const", const="trace")

    args = parser.parse_args(
        [
            "--tag",
            "api",
            "--tag",
            "cli",
            "--include",
            "src",
            "tests",
            "--include",
            "docs",
            "--debug-kind",
            "--trace-kind",
        ]
    )

    # 非空 append 默认序列会保留为结果前缀；它并非只在 option 缺席时使用。
    assert args.tag == ["base", "api", "cli"]
    assert args.include == ["src", "tests", "docs"]
    assert args.kinds == ["debug", "trace"]


def test_question_nargs_distinguishes_absent_bare_and_explicit_option():
    """option 的 nargs='?' 用 default/const/显式值表达三个状态。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--color", nargs="?", default="auto", const="always")

    assert parser.parse_args([]).color == "auto"
    assert parser.parse_args(["--color"]).color == "always"
    assert parser.parse_args(["--color", "never"]).color == "never"


def test_fixed_nargs_always_returns_lists_when_tokens_are_present():
    """nargs=1 也返回 list；option 缺席时 scalar default 不会自动装箱。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--one", nargs=1, type=int, default=7)
    parser.add_argument("--point", nargs=2, type=float)

    absent = parser.parse_args([])
    present = parser.parse_args(["--one", "8", "--point", "1.5", "2.5"])

    assert absent.one == 7
    assert present.one == [8]
    assert present.point == [1.5, 2.5]


def test_star_plus_and_remainder_have_different_consumption_contracts():
    """REMAINDER 保留后续 option-like token，适合转交给另一个命令解析器。"""

    list_parser = argparse.ArgumentParser()
    list_parser.add_argument("--labels", nargs="*")
    list_parser.add_argument("files", nargs="+")
    listed = list_parser.parse_args(
        ["--labels", "red", "blue", "--", "a.txt", "b.txt"]
    )

    command_parser = argparse.ArgumentParser()
    command_parser.add_argument("command")
    command_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    delegated = command_parser.parse_args(["tool", "--unknown", "value", "tail"])

    # 可变长 option 是贪婪的；``--`` 明确结束 labels，否则裸 token 都会被它消费。
    assert listed.labels == ["red", "blue"]
    assert listed.files == ["a.txt", "b.txt"]
    assert delegated.command == "tool"
    assert delegated.arguments == ["--unknown", "value", "tail"]


def test_only_string_defaults_are_passed_through_type_and_suppress_omits_dest():
    """非字符串 default 不经 type；SUPPRESS 让属性彻底缺席而不是值为 None。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default="1.5")
    parser.add_argument("--workers", type=float, default=2)
    parser.add_argument("--secret", default=argparse.SUPPRESS)

    args = parser.parse_args([])

    assert args.timeout == 1.5
    assert type(args.timeout) is float
    assert args.workers == 2
    assert type(args.workers) is int
    assert not hasattr(args, "secret")
