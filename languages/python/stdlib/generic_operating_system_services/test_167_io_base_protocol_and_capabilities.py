"""167｜``io`` hierarchy、stream capability、context manager 与 line iteration。

I/O category 由 text、buffered binary、raw binary 三层组成；具体 stream 可只实现其中
一部分操作。caller 应先理解 readable/writable/seekable 契约，并处理
``UnsupportedOperation``，而不是假设所有 file-like objects 都像磁盘文件。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.io.IOBase python.io.RawIOBase
# polyglot-covers: python.io.BufferedIOBase python.io.TextIOBase
# polyglot-covers: python.io.stream-hierarchy python.io.stream-capabilities
# polyglot-covers: python.io.UnsupportedOperation python.io.unsupported-operation-inheritance
# polyglot-covers: python.io.readable python.io.writable python.io.seekable
# polyglot-covers: python.io.stream-context-manager python.io.closed-stream-error
# polyglot-covers: python.io.stream-iteration python.io.readlines
# polyglot-covers: python.io.writelines python.io.writelines-no-separator

import io

import pytest


def test_unsupported_operation_is_both_oserror_and_valueerror():
    """双重继承兼容旧捕获方式；精确处理时仍应捕获 io.UnsupportedOperation。"""

    error = io.UnsupportedOperation("seek")

    assert isinstance(error, OSError)
    assert isinstance(error, ValueError)


def test_iobase_defaults_describe_a_stream_with_no_optional_capabilities():
    """IOBase 只给 protocol skeleton；subclass 按需实现 seek/read/write。"""

    stream = io.IOBase()

    assert stream.readable() is False
    assert stream.writable() is False
    assert stream.seekable() is False
    assert stream.isatty() is False
    with pytest.raises(io.UnsupportedOperation):
        stream.seek(0)
    with pytest.raises(io.UnsupportedOperation):
        stream.fileno()


def test_context_manager_closes_stream_even_when_suite_raises():
    """close 可重复调用；关闭后的 I/O 一般以 ValueError 表示 lifecycle error。"""

    stream = io.BytesIO(b"payload")
    with pytest.raises(RuntimeError, match="body failed"):
        with stream as entered:
            assert entered is stream
            raise RuntimeError("body failed")

    assert stream.closed is True
    stream.close()
    with pytest.raises(ValueError):
        stream.read()


def test_stream_iteration_and_readlines_preserve_line_terminators():
    """iteration 逐行产出，不自动 strip；EOF 后再次迭代不重新 rewind。"""

    stream = io.StringIO("first\nsecond\nlast")

    assert list(stream) == ["first\n", "second\n", "last"]
    assert list(stream) == []

    stream.seek(0)
    assert stream.readlines() == ["first\n", "second\n", "last"]


def test_writelines_does_not_insert_any_line_separator():
    """参数名是 lines，但元素可以没有 newline；separator 完全由 caller 提供。"""

    stream = io.StringIO()
    assert stream.writelines(["a", "b\n", "c"]) is None

    assert stream.getvalue() == "ab\nc"
