"""二进制缓冲区、视图与字节序。

共同问题：字节存储是否可变；视图是否共享内存；多字节整数如何选择端序；
复制与别名边界在哪里。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/python/builtins/test_022_binary_sequences.py
# polyglot-related: languages/python/stdlib/041-042_binary_data/test_041_struct_binary_layouts.py

import struct

import pytest


def test_bytes_is_immutable_and_bytearray_is_mutable():
    immutable = b"abc"
    mutable = bytearray(immutable)

    with pytest.raises(TypeError):
        immutable[0] = ord("z")

    mutable[0] = ord("z")
    assert mutable == bytearray(b"zbc")


def test_memoryview_shares_the_exporter_storage():
    storage = bytearray(b"abc")
    view = memoryview(storage)[1:]

    view[0] = ord("z")

    assert storage == bytearray(b"azc")
    assert view.obj is storage


def test_struct_makes_endianness_explicit():
    value = 0x01020304

    assert struct.pack(">I", value) == b"\x01\x02\x03\x04"
    assert struct.pack("<I", value) == b"\x04\x03\x02\x01"
    assert struct.unpack(">I", b"\x01\x02\x03\x04") == (value,)


def test_bytes_slice_copies_while_memoryview_slice_remains_a_view():
    storage = bytearray(b"abc")
    copied = bytes(storage)[1:]
    shared = memoryview(storage)[1:]
    storage[1] = ord("z")

    assert copied == b"bc"
    assert bytes(shared) == b"zc"
