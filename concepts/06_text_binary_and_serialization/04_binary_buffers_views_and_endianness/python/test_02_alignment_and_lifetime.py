"""未对齐访问、视图生命周期与复制边界。

共同问题：多字节访问是否要求对齐；共享视图何时阻止或失去底层存储；
协议读取如何避免依赖宿主对象布局。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/python/stdlib/041-042_binary_data/test_041_struct_binary_layouts.py
# polyglot-related: languages/python/builtins/test_022_binary_sequences.py

import struct

import pytest


def test_struct_reads_explicit_endian_value_from_an_odd_offset():
    storage = bytearray(b"\x00\x01\x02\x03\x04")

    assert struct.unpack_from(">I", storage, 1) == (0x01020304,)

    struct.pack_into("<I", storage, 1, 0x01020304)
    assert storage == bytearray(b"\x00\x04\x03\x02\x01")

    # struct 逐字节处理指定 offset，不把 buffer 强转为需要自然对齐的机器整数引用。


def test_exported_memoryview_blocks_resize_until_release():
    storage = bytearray(b"abc")
    view = memoryview(storage)

    with pytest.raises(BufferError):
        storage.extend(b"d")

    view.release()
    storage.extend(b"d")
    assert storage == bytearray(b"abcd")


def test_tobytes_copies_before_the_view_is_released():
    storage = bytearray(b"abc")
    view = memoryview(storage)[1:]
    copied = view.tobytes()

    view.release()
    storage[1] = ord("z")

    assert copied == b"bc"
    assert storage == bytearray(b"azc")
