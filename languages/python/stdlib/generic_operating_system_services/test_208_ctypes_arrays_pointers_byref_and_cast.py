"""208｜``ctypes`` array、typed pointer、``byref`` 与 ``cast`` aliasing。

``T * n`` 创建固定长度 array type；``POINTER(T)`` 创建并缓存 typed pointer type。
pointer/contents/byref/cast 都可能让多个 Python wrapper 指向同一块 C 内存，不会复制值。
pointer 没有长度元数据，越界读写可能崩溃，案例只访问已知有效范围。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.Array python.ctypes.array-type-multiplication
# polyglot-covers: python.ctypes.Array._length_ python.ctypes.Array._type_
# polyglot-covers: python.ctypes.array-index python.ctypes.array-slice
# polyglot-covers: python.ctypes.POINTER python.ctypes.POINTER-type-cache
# polyglot-covers: python.ctypes.pointer python.ctypes.pointer.contents
# polyglot-covers: python.ctypes.pointer-wrapper-not-identity
# polyglot-covers: python.ctypes.null-pointer python.ctypes.null-pointer-contents-error
# polyglot-covers: python.ctypes.byref python.ctypes.byref-offset
# polyglot-covers: python.ctypes.cast python.ctypes.array-to-pointer
# polyglot-covers: python.ctypes.pointer-no-bounds-check

import ctypes

import pytest


def test_array_type_has_fixed_length_zero_initialization_and_list_slices():
    """slice read 返回普通 list，不保留 C array type 或 alias。"""

    Vector = ctypes.c_int * 4
    values = Vector(1, 2)

    assert Vector._length_ == 4
    assert Vector._type_ is ctypes.c_int
    assert len(values) == 4
    assert values[:] == [1, 2, 0, 0]
    assert type(values[:]) is list

    values[2] = 7
    snapshot = values[1:3]
    values[1] = 9
    assert snapshot == [2, 7]
    assert values[:] == [1, 9, 7, 0]


def test_pointer_contents_aliases_value_but_returns_fresh_python_wrappers():
    """``ptr.contents is ptr.contents`` 为 false，不代表底层 C object 不同。"""

    value = ctypes.c_int(10)
    pointer = ctypes.pointer(value)
    first_wrapper = pointer.contents
    second_wrapper = pointer.contents

    assert first_wrapper is not second_wrapper
    assert ctypes.addressof(first_wrapper) == ctypes.addressof(value)
    assert ctypes.addressof(second_wrapper) == ctypes.addressof(value)

    pointer.contents.value = 25
    assert value.value == 25
    value.value = 30
    assert pointer[0] == 30


def test_pointer_factory_is_cached_and_null_pointer_is_false():
    """空 typed pointer 可传给接受 NULL 的 C API，但解引用会抛 ValueError。"""

    IntPointer = ctypes.POINTER(ctypes.c_int)

    assert IntPointer is ctypes.POINTER(ctypes.c_int)
    null = IntPointer()
    assert bool(null) is False
    with pytest.raises(ValueError, match="NULL pointer access"):
        _ = null.contents


def test_array_can_decay_to_pointer_for_known_valid_element_range():
    """cast 不附加长度；这里只由原 array 的生命周期和长度证明三次索引安全。"""

    values = (ctypes.c_int * 3)(4, 5, 6)
    pointer = ctypes.cast(values, ctypes.POINTER(ctypes.c_int))

    assert [pointer[index] for index in range(len(values))] == [4, 5, 6]
    pointer[1] = 50
    assert values[:] == [4, 50, 6]


def test_byref_offset_addresses_a_subobject_without_allocating_pointer_object():
    """byref 是传参优化对象；需要索引/contents 时可显式 cast 为 typed pointer。"""

    pair = (ctypes.c_int * 2)(11, 22)
    second_reference = ctypes.byref(pair, ctypes.sizeof(ctypes.c_int))
    second_pointer = ctypes.cast(second_reference, ctypes.POINTER(ctypes.c_int))

    assert second_pointer.contents.value == 22
    second_pointer.contents.value = 33
    assert pair[:] == [11, 33]


def test_cast_can_reinterpret_owned_buffer_address_as_char_pointer():
    """cast 只改变 Python 侧 type view；buffer 必须保持存活以保证地址有效。"""

    buffer = ctypes.create_string_buffer(b"hello")
    pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))

    assert pointer[0] == b"h"
    pointer[1] = b"A"
    assert buffer.value == b"hAllo"
