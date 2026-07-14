"""184｜``getopt.gnu_getopt`` 的 intermixed 扫描、长 option 前缀与错误对象。

GNU 模式默认允许 option 与 operand 穿插，但 ``+`` shortopts 前缀或环境变量
``POSIXLY_CORRECT`` 会恢复遇到 operand 即停止的规则。long option 允许唯一前缀，
因此扩充 option 集可能让过去的缩写突然产生歧义；稳定接口应鼓励完整拼写。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.getopt.gnu_getopt python.getopt.gnu-intermixed-scanning
# polyglot-covers: python.getopt.gnu-leading-plus python.getopt.POSIXLY_CORRECT
# polyglot-covers: python.getopt.long-option-unique-prefix
# polyglot-covers: python.getopt.long-option-ambiguous-prefix
# polyglot-covers: python.getopt.GetoptError python.getopt.GetoptError.msg
# polyglot-covers: python.getopt.GetoptError.opt python.getopt.error-alias
# polyglot-covers: python.getopt.unknown-option-error
# polyglot-covers: python.getopt.missing-option-argument-error
# polyglot-covers: python.getopt.unexpected-long-option-argument-error

import getopt

import pytest


def test_gnu_scanning_collects_options_while_preserving_operand_order():
    """intermixed 只改变扫描顺序；options 与 operands 各自在结果中维持出现顺序。"""

    options, operands = getopt.gnu_getopt(
        ["first", "-v", "second", "--output", "result", "third"],
        "v",
        ["output="],
    )

    assert options == [("-v", ""), ("--output", "result")]
    assert operands == ["first", "second", "third"]


def test_leading_plus_and_posix_environment_restore_stop_at_operand(monkeypatch):
    """两种 POSIX 开关都使第一个 operand 后的 option 保持未解析。"""

    tokens = ["first", "-v", "second"]
    leading_plus = getopt.gnu_getopt(tokens, "+v")

    monkeypatch.setenv("POSIXLY_CORRECT", "1")
    environment = getopt.gnu_getopt(tokens, "v")

    assert leading_plus == ([], tokens)
    assert environment == ([], tokens)


def test_unique_long_prefix_expands_to_the_declared_full_name():
    """``--fo`` 只匹配 foo；``--f`` 同时匹配 foo/frob，因而不能猜测。"""

    options, operands = getopt.getopt(["--fo", "payload"], "", ["foo", "frob"])

    assert options == [("--foo", "")]
    assert operands == ["payload"]

    with pytest.raises(getopt.GetoptError) as raised:
        getopt.getopt(["--f"], "", ["foo", "frob"])

    assert raised.value.msg == "option --f not a unique prefix"
    assert raised.value.opt == "f"
    assert str(raised.value) == raised.value.msg


@pytest.mark.parametrize(
    ("tokens", "shortopts", "longopts", "expected_opt", "message_fragment"),
    [
        (["-x"], "v", [], "x", "not recognized"),
        (["-o"], "o:", [], "o", "requires argument"),
        (["--verbose=yes"], "", ["verbose"], "verbose", "must not have an argument"),
    ],
)
def test_malformed_options_expose_machine_readable_error_context(
    tokens,
    shortopts,
    longopts,
    expected_opt,
    message_fragment,
):
    """调用方可用 opt 定位问题；不要解析本地化后的 msg 文本来恢复 option。"""

    with pytest.raises(getopt.GetoptError) as raised:
        getopt.getopt(tokens, shortopts, longopts)

    assert raised.value.opt == expected_opt
    assert message_fragment in raised.value.msg
    assert getopt.error is getopt.GetoptError
