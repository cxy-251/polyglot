"""172｜``StringIO``、high-level aliases、``open_code`` 与 Python 3.10 encoding helper。

StringIO 是 character stream，不执行 codec；构造后的 cursor 位于开头，首次 write
会 overwrite 而非 append。``open_code`` 用 binary mode 表达“把文件当可执行代码”
的意图；公开 API 接受 optional encoding 时可用 ``text_encoding`` 标出 locale choice。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.io.StringIO python.io.StringIO.getvalue
# polyglot-covers: python.io.stringio-initial-position python.io.stringio-overwrite
# polyglot-covers: python.io.stringio-newline-translation
# polyglot-covers: python.io.open python.io.open-alias
# polyglot-covers: python.io.open-code python.io.executable-code-binary-open
# polyglot-covers: python.io.text-encoding-helper python.io.EncodingWarning
# polyglot-covers: python.io.BlockingIOError python.io.text-binary-type-error

import builtins
import io

import pytest


def test_stringio_initial_cursor_overwrites_and_getvalue_ignores_position():
    """若要 append，应显式 seek(SEEK_END)；getvalue 不移动当前 cursor。"""

    stream = io.StringIO("abcdef")
    assert stream.tell() == 0
    assert stream.write("XY") == 2
    before = stream.tell()

    assert stream.getvalue() == "XYcdef"
    assert stream.tell() == before

    stream.seek(0, io.SEEK_END)
    stream.write("!")
    assert stream.getvalue() == "XYcdef!"


def test_stringio_can_translate_written_newlines_without_using_an_encoding():
    """newline 处理属于 text layer；StringIO 始终存 str，不生成 bytes。"""

    stream = io.StringIO(newline="\r\n")
    stream.write("a\nb")

    assert stream.getvalue() == "a\r\nb"


def test_io_open_alias_and_open_code_binary_contract(tmp_path):
    """open_code 需要 absolute str path，并返回可 seek 的 binary stream。"""

    path = tmp_path / "module.py"
    path.write_text("answer = 42\n", encoding="utf-8")

    assert io.open is builtins.open
    with io.open_code(str(path.resolve())) as stream:
        assert stream.read() == b"answer = 42\n"
        assert stream.mode == "rb"


def test_text_encoding_marks_explicit_or_locale_choice_for_api_authors():
    """warn_default_encoding flag 开启时，None 路径还会在 caller 位置发 warning。"""

    assert io.text_encoding("utf-8") == "utf-8"
    assert io.text_encoding(None) == "locale"
    assert issubclass(EncodingWarning, Warning)


def test_text_and_binary_streams_reject_cross_category_values():
    """codec boundary 不能靠隐式转换；caller 必须明确 encode/decode。"""

    with pytest.raises(TypeError):
        io.BytesIO().write("text")
    with pytest.raises(TypeError):
        io.StringIO().write(b"bytes")

    assert io.BlockingIOError is BlockingIOError
