"""171｜``TextIOWrapper`` encoding/errors/newlines、opaque tell cookie 与 detach。

text stream 的 position 是 decoder state cookie，不应当成 byte offset 运算。newline
参数同时控制 read recognition/translation 与 write translation；encoding 应显式给出，
避免 locale-dependent defaults。detach 后 wrapper 不可用，binary buffer 归 caller。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.io.TextIOWrapper python.io.text-binary-layering
# polyglot-covers: python.io.text-encoding python.io.text-errors
# polyglot-covers: python.io.universal-newlines python.io.TextIOBase.newlines
# polyglot-covers: python.io.text-write-newline-translation
# polyglot-covers: python.io.text-tell-cookie python.io.text-seek-cookie
# polyglot-covers: python.io.TextIOWrapper.detach python.io.text-detach-ownership
# polyglot-covers: python.io.TextIOWrapper.reconfigure python.io.reconfigure-read-limit
# polyglot-covers: python.io.line-buffering python.io.write-through

import io

import pytest


def test_universal_newline_read_normalizes_three_terminators_and_records_them():
    """newline=None 把 CR/LF/CRLF 都返回为 LF；newlines 记录已观察类型。"""

    binary = io.BytesIO(b"a\r\nb\rc\n")
    text = io.TextIOWrapper(binary, encoding="ascii", newline=None)

    assert text.read() == "a\nb\nc\n"
    assert set(text.newlines) == {"\r", "\n", "\r\n"}


def test_empty_newline_recognizes_all_terminators_but_returns_them_untranslated():
    """newline='' 常用于 parser 必须保留原始行尾的场景。"""

    text = io.TextIOWrapper(
        io.BytesIO(b"a\r\nb\rc\n"),
        encoding="ascii",
        newline="",
    )

    assert text.readlines() == ["a\r\n", "b\r", "c\n"]


def test_write_newline_translation_and_explicit_error_policy():
    """newline='\r\n' 转换输入 LF；errors='backslashreplace' 避免静默丢字符。"""

    binary = io.BytesIO()
    text = io.TextIOWrapper(
        binary,
        encoding="ascii",
        errors="backslashreplace",
        newline="\r\n",
    )
    text.write("café\n")
    text.flush()

    assert binary.getvalue() == b"caf\\xe9\r\n"
    assert text.encoding == "ascii"
    assert text.errors == "backslashreplace"


def test_text_tell_value_is_only_reused_as_an_opaque_seek_cookie():
    """multibyte decoder 可预读 binary data；只保存并传回 cookie，不自行加减。"""

    text = io.TextIOWrapper(io.BytesIO("甲乙丙".encode("utf-8")), encoding="utf-8")
    assert text.read(1) == "甲"
    cookie = text.tell()
    assert text.read(1) == "乙"

    assert text.seek(cookie) == cookie
    assert text.read(1) == "乙"
    with pytest.raises(io.UnsupportedOperation):
        text.seek(1, io.SEEK_CUR)


def test_detach_transfers_binary_buffer_and_invalidates_text_wrapper():
    """flush 后 detach，避免 bytes 留在 wrapper；返回 buffer 由 caller close。"""

    binary = io.BytesIO()
    text = io.TextIOWrapper(binary, encoding="utf-8")
    text.write("中文")
    text.flush()
    detached = text.detach()
    try:
        assert detached.getvalue() == "中文".encode("utf-8")
        with pytest.raises(ValueError):
            text.write("unusable")
    finally:
        detached.close()


def test_reconfigure_after_write_flushes_but_after_read_cannot_change_encoding():
    """write 后允许换 encoding；首次 read 后 decoder state 阻止变更。"""

    binary = io.BytesIO()
    writer = io.TextIOWrapper(binary, encoding="utf-8")
    writer.write("é")
    writer.reconfigure(encoding="utf-16-le", write_through=True)
    writer.write("甲")
    writer.flush()
    assert binary.getvalue() == "é".encode("utf-8") + "甲".encode("utf-16-le")
    assert writer.write_through is True

    reader = io.TextIOWrapper(io.BytesIO(b"abc"), encoding="ascii")
    assert reader.read(1) == "a"
    with pytest.raises(io.UnsupportedOperation):
        reader.reconfigure(encoding="utf-8")


def test_line_buffering_flushes_when_write_contains_newline():
    """line_buffering 检测 newline/CR；没有换行的 write 不保证立即下沉。"""

    binary = io.BytesIO()
    text = io.TextIOWrapper(binary, encoding="ascii", line_buffering=True)
    text.write("line\n")

    assert text.line_buffering is True
    assert binary.getvalue() == b"line\n"
