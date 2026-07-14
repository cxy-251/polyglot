"""200｜``curses.ascii`` 的 locale-independent ASCII 分类与位变换。

这些函数只解释 7-bit ASCII 数值，接受整数或单字符字符串；它们不等同于 Unicode
``str.is*``。``ctrl`` 清除高三位，``alt`` 设置 meta bit，``ascii`` 清除 meta bit，
而 ``unctrl`` 把控制字符转为适合终端展示的 caret notation。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.curses.ascii-control-constants
# polyglot-covers: python.curses.ascii.isascii python.curses.ascii.isalnum
# polyglot-covers: python.curses.ascii.isalpha python.curses.ascii.isblank
# polyglot-covers: python.curses.ascii.iscntrl python.curses.ascii.isctrl
# polyglot-covers: python.curses.ascii.isdigit python.curses.ascii.isgraph
# polyglot-covers: python.curses.ascii.islower python.curses.ascii.ismeta
# polyglot-covers: python.curses.ascii.isprint python.curses.ascii.ispunct
# polyglot-covers: python.curses.ascii.isspace python.curses.ascii.isupper
# polyglot-covers: python.curses.ascii.isxdigit
# polyglot-covers: python.curses.ascii.ascii python.curses.ascii.ctrl
# polyglot-covers: python.curses.ascii.alt python.curses.ascii.unctrl

import curses.ascii as ascii_tools

import pytest


@pytest.mark.parametrize(
    ("function", "accepted", "rejected"),
    [
        (ascii_tools.isalnum, "A", "!"),
        (ascii_tools.isalpha, "z", "7"),
        (ascii_tools.isblank, "\t", "\n"),
        (ascii_tools.iscntrl, ascii_tools.DEL, " "),
        (ascii_tools.isctrl, ascii_tools.NUL, ascii_tools.DEL),
        (ascii_tools.isdigit, "9", "a"),
        (ascii_tools.isgraph, "!", " "),
        (ascii_tools.islower, "a", "A"),
        (ascii_tools.isprint, " ", "\n"),
        (ascii_tools.ispunct, "?", "Q"),
        (ascii_tools.isspace, "\r", "x"),
        (ascii_tools.isupper, "Z", "z"),
        (ascii_tools.isxdigit, "f", "g"),
    ],
)
def test_ascii_character_classes_have_explicit_7_bit_boundaries(
    function,
    accepted,
    rejected,
):
    assert function(accepted) is True
    assert function(rejected) is False


def test_ascii_and_meta_membership_do_not_follow_unicode_categories():
    """0x80 以上是 meta；非 ASCII Unicode 字母不会因 isalpha 而被接受。"""

    assert ascii_tools.isascii(0) is True
    assert ascii_tools.isascii(127) is True
    assert ascii_tools.isascii(128) is False
    assert ascii_tools.ismeta(128) is True
    assert ascii_tools.ismeta("é") is True
    assert ascii_tools.isalpha("é") is False


def test_bit_transformations_preserve_string_or_integer_result_kind():
    """输入 str 返回 str，输入 int 返回 int；这些操作本质都是 bit mask。"""

    assert ascii_tools.ctrl("C") == "\x03"
    assert ascii_tools.ctrl(ord("C")) == 3
    assert ascii_tools.alt("A") == chr(0xC1)
    assert ascii_tools.alt(ord("A")) == 0xC1
    assert ascii_tools.ascii(chr(0xC1)) == "A"
    assert ascii_tools.ascii(0xC1) == ord("A")


def test_unctrl_uses_caret_and_meta_notation():
    """DEL 特判为 ^?；高位字符先加 !，再展示其低 7 位形式。"""

    assert ascii_tools.unctrl(ascii_tools.NUL) == "^@"
    assert ascii_tools.unctrl("\x01") == "^A"
    assert ascii_tools.unctrl(ascii_tools.DEL) == "^?"
    assert ascii_tools.unctrl("A") == "A"
    assert ascii_tools.unctrl(ascii_tools.alt("A")) == "!A"


def test_control_constant_aliases_match_terminal_conventions():
    """HT/TAB 与 LF/NL 是历史命名别名；SP 是唯一命名的普通空格。"""

    assert ascii_tools.HT == ascii_tools.TAB == 9
    assert ascii_tools.LF == ascii_tools.NL == 10
    assert ascii_tools.ESC == 27
    assert ascii_tools.SP == 32
    assert ascii_tools.controlnames[ascii_tools.ESC] == "ESC"


def test_string_inputs_must_contain_exactly_one_character():
    """内部使用 ord；多字符字符串是调用错误，不会逐字符分类。"""

    with pytest.raises(TypeError):
        ascii_tools.isdigit("12")
