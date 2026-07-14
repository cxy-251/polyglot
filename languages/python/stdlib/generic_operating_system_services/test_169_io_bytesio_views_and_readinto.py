"""169｜``BytesIO`` random access、readinto 与 zero-copy ``getbuffer`` view。

``getvalue`` 复制并忽略 cursor；``getbuffer`` 返回共享 writable view。共享 view
存活期间 buffer 不能 resize 或 close，这是常见 ``BufferError`` 来源。
预分配目标时，
``readinto`` 可避免为结果再创建 bytes object。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.io.BytesIO python.io.BytesIO.getvalue
# polyglot-covers: python.io.BytesIO.seek python.io.BytesIO.truncate
# polyglot-covers: python.io.BytesIO.readinto python.io.BytesIO.readinto1
# polyglot-covers: python.io.BytesIO.getbuffer python.io.zero-copy-buffer-view
# polyglot-covers: python.io.bytesio-view-mutation python.io.bytesio-view-resize-lock
# polyglot-covers: python.io.BufferError python.io.memoryview-release

import io

import pytest


def test_bytesio_cursor_overwrite_append_and_truncate_are_independent_of_getvalue():
    """构造后 cursor 在开头；write 默认 overwrite，seek(end) 后才 append。"""

    stream = io.BytesIO(b"abcdef")
    assert stream.tell() == 0
    assert stream.write(b"XY") == 2
    assert stream.getvalue() == b"XYcdef"

    stream.seek(0, io.SEEK_END)
    stream.write(b"!")
    assert stream.getvalue() == b"XYcdef!"

    stream.seek(3)
    assert stream.truncate() == 3
    assert stream.tell() == 3
    assert stream.getvalue() == b"XYc"


def test_readinto_and_readinto1_fill_existing_mutable_buffers():
    """返回 count 决定有效 prefix；目标 buffer 多余部分保持原值。"""

    stream = io.BytesIO(b"abcdef")
    first = bytearray(b"xxxx")
    second = bytearray(b"yyy")

    assert stream.readinto(first) == 4
    assert first == b"abcd"
    assert stream.readinto1(second) == 2
    assert second == b"efy"


def test_getbuffer_view_mutates_owner_and_temporarily_prevents_resize_or_close():
    """release view 后 owner 才能 resize/close；del view 也可释放 export。"""

    stream = io.BytesIO(b"abcdef")
    view = stream.getbuffer()
    view[2:4] = b"XY"

    assert stream.getvalue() == b"abXYef"
    stream.seek(0, io.SEEK_END)
    with pytest.raises(BufferError):
        stream.write(b"more")
    with pytest.raises(BufferError):
        stream.close()

    view.release()
    stream.seek(0, io.SEEK_END)
    assert stream.write(b"!") == 1
    stream.close()
    assert stream.closed is True
