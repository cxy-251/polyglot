"""215｜``ctypes`` address/size/alignment、raw memory utilities 与 ``resize``。

``addressof``/``string_at``/``memmove`` 等 API 直接操作 native address，不携带 ownership
或边界信息；案例只使用仍存活的 ctypes-owned buffer 和已知长度。``resize`` 可扩大 backing
store，却不会改变原 array type 的 ``_length_``，所以新增空间仍需通过正确 pointer view 访问。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.addressof python.ctypes.sizeof
# polyglot-covers: python.ctypes.alignment python.ctypes.native-address
# polyglot-covers: python.ctypes.memmove python.ctypes.memset
# polyglot-covers: python.ctypes.string_at python.ctypes.string_at-explicit-size
# polyglot-covers: python.ctypes.wstring_at
# polyglot-covers: python.ctypes.resize python.ctypes.resize-grow
# polyglot-covers: python.ctypes.resize-type-length-trap
# polyglot-covers: python.ctypes.resize-smaller-error

import ctypes

import pytest


class AlignedRecord(ctypes.Structure):
    _fields_ = [("tag", ctypes.c_char), ("value", ctypes.c_int)]


def test_size_alignment_and_address_describe_native_storage():
    """sizeof(instance/type) 一致；structure address 满足其 alignment 倍数约束。"""

    record = AlignedRecord(tag=b"A", value=42)

    assert ctypes.sizeof(record) == ctypes.sizeof(AlignedRecord)
    assert ctypes.alignment(record) == ctypes.alignment(AlignedRecord)
    assert ctypes.addressof(record) % ctypes.alignment(record) == 0
    with pytest.raises(TypeError):
        ctypes.addressof(b"not a ctypes object")


def test_memmove_and_memset_mutate_only_the_known_buffer_range():
    """memmove 支持重叠区间；这里使用独立 source，并以 byref offset 定位 destination。"""

    buffer = ctypes.create_string_buffer(b"abcdef")
    source = ctypes.create_string_buffer(b"XYZ")

    ctypes.memmove(ctypes.byref(buffer, 1), source, 3)
    ctypes.memset(ctypes.byref(buffer, 4), ord("!"), 2)

    assert buffer.value == b"aXYZ!!"
    assert ctypes.string_at(ctypes.addressof(buffer)) == b"aXYZ!!"
    assert ctypes.string_at(ctypes.addressof(buffer), 3) == b"aXY"


def test_wstring_at_reads_owned_wchar_storage_until_nul():
    """wstring_at 的 size 单位是 wchar_t 元素；省略时读取到首个 wide NUL。"""

    buffer = ctypes.create_unicode_buffer("猫狗")

    assert ctypes.wstring_at(ctypes.addressof(buffer)) == "猫狗"
    assert ctypes.wstring_at(ctypes.addressof(buffer), 1) == "猫"


def test_resize_grows_storage_but_not_the_array_types_index_contract():
    """扩大后的 sizeof 已变化，len/index 仍由最初 ``c_short * 4`` type 决定。"""

    Numbers = ctypes.c_short * 4
    values = Numbers(1, 2, 3, 4)
    expanded_size = ctypes.sizeof(ctypes.c_short) * 8

    ctypes.resize(values, expanded_size)

    assert ctypes.sizeof(values) == expanded_size
    assert len(values) == 4
    assert values[:] == [1, 2, 3, 4]
    with pytest.raises(IndexError):
        _ = values[4]

    expanded_view = ctypes.cast(values, ctypes.POINTER(ctypes.c_short))
    expanded_view[4] = 9
    assert expanded_view[4] == 9


def test_resize_rejects_size_smaller_than_natural_object_size():
    """不能用 resize 截断 type 声明的必要 storage。"""

    values = (ctypes.c_int * 2)(1, 2)

    with pytest.raises(ValueError, match="minimum size"):
        ctypes.resize(values, ctypes.sizeof(ctypes.c_int))
