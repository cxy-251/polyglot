"""209｜``ctypes.Structure``/``Union`` layout、packing、anonymous 与 bit fields。

``_fields_`` 的顺序决定 C layout，descriptor 暴露 offset/size；``_pack_`` 必须在 fields
之前声明。Union 的所有字段共享地址，解释哪一个字段有效由外部 tag/protocol 决定。
bit field 顺序与 ABI 有关，含 bit field 的结构不应按值传给 foreign function。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.Structure python.ctypes.Structure._fields_
# polyglot-covers: python.ctypes.structure-positional-initialization
# polyglot-covers: python.ctypes.structure-keyword-initialization
# polyglot-covers: python.ctypes.CField-offset python.ctypes.CField-size
# polyglot-covers: python.ctypes.structure-size-layout
# polyglot-covers: python.ctypes.structure-alignment-layout
# polyglot-covers: python.ctypes.Structure._pack_
# polyglot-covers: python.ctypes.Union python.ctypes.union-shared-storage
# polyglot-covers: python.ctypes.Structure._anonymous_
# polyglot-covers: python.ctypes.bit-fields python.ctypes.bit-field-truncation
# polyglot-covers: python.ctypes.bit-field-by-value-caveat

import ctypes
import sys


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]


class Rectangle(ctypes.Structure):
    _fields_ = [("upper_left", Point), ("lower_right", Point)]


class NaturalLayout(ctypes.Structure):
    _fields_ = [("tag", ctypes.c_char), ("value", ctypes.c_int)]


class PackedLayout(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("tag", ctypes.c_char), ("value", ctypes.c_int)]


class NumberBytes(ctypes.Union):
    _fields_ = [("number", ctypes.c_uint32), ("octets", ctypes.c_ubyte * 4)]


class TaggedNumber(ctypes.Structure):
    _anonymous_ = ("payload",)
    _fields_ = [("kind", ctypes.c_ubyte), ("payload", NumberBytes)]


class Flags(ctypes.Structure):
    _fields_ = [
        ("ready", ctypes.c_uint, 1),
        ("mode", ctypes.c_uint, 3),
        ("reserved", ctypes.c_uint, 28),
    ]


def test_structure_constructor_and_field_descriptors_follow_declared_order():
    """未知 keyword 只是普通 Python attribute，不会自动成为 C field。"""

    point = Point(3, y=4)
    point.label = "debug-only"
    rectangle = Rectangle(point, Point(8, 9))

    assert (point.x, point.y) == (3, 4)
    assert point.label == "debug-only"
    assert (rectangle.upper_left.x, rectangle.lower_right.y) == (3, 9)
    assert Point.x.offset == 0
    assert Point.y.offset == ctypes.sizeof(ctypes.c_int)
    assert Point.x.size == ctypes.sizeof(ctypes.c_int)


def test_pack_removes_natural_padding_and_changes_field_offset():
    """pack=1 常用于 wire/file layout；直接映射 native ABI 时通常保留自然对齐。"""

    assert NaturalLayout.value.offset % ctypes.alignment(ctypes.c_int) == 0
    assert PackedLayout.value.offset == 1
    assert ctypes.sizeof(PackedLayout) == 1 + ctypes.sizeof(ctypes.c_int)
    assert ctypes.sizeof(NaturalLayout) >= ctypes.sizeof(PackedLayout)


def test_union_fields_are_two_views_over_the_same_native_endian_bytes():
    """整数写入后 byte array 顺序取决于当前 native byte order。"""

    value = NumberBytes(number=0x01020304)

    assert bytes(value.octets) == (0x01020304).to_bytes(4, sys.byteorder)
    value.octets[0] = 0xFF
    assert value.number == int.from_bytes(bytes(value.octets), sys.byteorder)


def test_anonymous_union_promotes_nested_fields_to_outer_structure():
    """promoted descriptor 与 explicit payload.field 访问同一 storage。"""

    tagged = TaggedNumber(kind=1)
    tagged.number = 0xAABBCCDD

    assert tagged.payload.number == 0xAABBCCDD
    tagged.payload.octets[0] = 0
    assert tagged.number == tagged.payload.number


def test_bit_fields_mask_assigned_values_to_declared_width():
    """1-bit/3-bit 字段只保留低位；符号与布局仍由声明 type 和平台 ABI 决定。"""

    flags = Flags()
    flags.ready = 3
    flags.mode = 15

    assert flags.ready == 1
    assert flags.mode == 7
    assert ctypes.sizeof(flags) == ctypes.sizeof(ctypes.c_uint)
