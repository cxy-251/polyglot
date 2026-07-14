"""183｜``getopt.getopt`` 的 C/Unix 风格 option 扫描与返回协议。

``getopt`` 不生成 Namespace，也不负责帮助文本；它只返回有序的 ``(option, value)``
pair 和剩余 operand。short option 后的冒号、long option 后的等号是在声明“必须有值”，
不是命令行拼写的一部分。遇到第一个非 option 后，传统扫描立即停止。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.getopt.getopt python.getopt.shortopts
# polyglot-covers: python.getopt.short-option-cluster
# polyglot-covers: python.getopt.short-option-required-argument
# polyglot-covers: python.getopt.short-option-attached-argument
# polyglot-covers: python.getopt.longopts python.getopt.long-option-required-argument
# polyglot-covers: python.getopt.long-option-equals-value
# polyglot-covers: python.getopt.option-value-pairs python.getopt.repeated-options
# polyglot-covers: python.getopt.stop-at-first-operand
# polyglot-covers: python.getopt.double-dash python.getopt.lone-dash

import getopt


def test_short_options_preserve_order_and_support_attached_values():
    """cluster 逐字展开；需要值的 option 会消费 cluster 余串或下一个 token。"""

    options, operands = getopt.getopt(
        ["-av", "-bfast", "-c", "slow", "input.txt"],
        "avb:c:",
    )

    assert options == [
        ("-a", ""),
        ("-v", ""),
        ("-b", "fast"),
        ("-c", "slow"),
    ]
    assert operands == ["input.txt"]


def test_long_options_accept_separate_or_equals_values_and_can_repeat():
    """返回名称会规范为完整 ``--name``，但值始终是字符串。"""

    options, operands = getopt.getopt(
        [
            "--verbose",
            "--output=first.txt",
            "--output",
            "second.txt",
            "payload",
        ],
        "",
        ["verbose", "output="],
    )

    assert options == [
        ("--verbose", ""),
        ("--output", "first.txt"),
        ("--output", "second.txt"),
    ]
    assert operands == ["payload"]


def test_traditional_scanning_leaves_everything_after_the_first_operand():
    """后续 ``-v`` 不再解释为 option；返回 operands 是原参数的 trailing slice。"""

    options, operands = getopt.getopt(
        ["-a", "first", "-v", "second"],
        "av",
    )

    assert options == [("-a", "")]
    assert operands == ["first", "-v", "second"]


def test_double_dash_ends_scanning_while_lone_dash_is_an_operand():
    """``--`` 被丢弃；单独 ``-`` 本身保留，并像普通 operand 一样终止传统扫描。"""

    terminated = getopt.getopt(["-v", "--", "-x", "tail"], "vx")
    lone_dash = getopt.getopt(["-", "-v"], "v")

    assert terminated == ([("-v", "")], ["-x", "tail"])
    assert lone_dash == ([], ["-", "-v"])
