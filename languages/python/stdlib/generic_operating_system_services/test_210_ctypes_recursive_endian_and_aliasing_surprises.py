"""210｜``ctypes`` incomplete recursive types、endian structures 与 wrapper alias trap。

递归结构要先声明空 class，再赋 ``_fields_``，这样才能创建指向自身的 POINTER type。
nested structure 属性返回引用父 buffer 的 wrapper，不是独立副本，因此直接 tuple-swap
会因第一次写入改变第二个 wrapper 所见内存。跨字节序结构则禁止 pointer fields。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.incomplete-Structure
# polyglot-covers: python.ctypes.recursive-Structure python.ctypes.self-pointer
# polyglot-covers: python.ctypes.Structure-fields-final
# polyglot-covers: python.ctypes.structure-inheritance
# polyglot-covers: python.ctypes.nested-structure-wrapper-alias
# polyglot-covers: python.ctypes.structure-tuple-swap-trap
# polyglot-covers: python.ctypes.BigEndianStructure
# polyglot-covers: python.ctypes.LittleEndianStructure
# polyglot-covers: python.ctypes.endian-structure-pointer-prohibition

import ctypes
import sys

import pytest


class Cell(ctypes.Structure):
    pass


Cell._fields_ = [("value", ctypes.c_int), ("next", ctypes.POINTER(Cell))]


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]


class Pair(ctypes.Structure):
    _fields_ = [("first", Point), ("second", Point)]


class Header(ctypes.Structure):
    _fields_ = [("kind", ctypes.c_ubyte)]


class Packet(Header):
    _fields_ = [("length", ctypes.c_uint16)]


class NetworkWord(ctypes.BigEndianStructure):
    _fields_ = [("value", ctypes.c_uint16)]


class LittleWord(ctypes.LittleEndianStructure):
    _fields_ = [("value", ctypes.c_uint16)]


def test_recursive_structure_links_nodes_and_null_terminates_chain():
    """pointer(target) 也保持 target 存活；最后一个默认 pointer 是 NULL。"""

    tail = Cell(value=2)
    head = Cell(value=1, next=ctypes.pointer(tail))

    assert head.next.contents.value == 2
    assert bool(tail.next) is False
    head.next.contents.value = 20
    assert tail.value == 20


def test_fields_become_final_after_type_has_been_used():
    """先实例化 incomplete type 会冻结 layout，之后不能再补 fields。"""

    class UsedTooEarly(ctypes.Structure):
        pass

    UsedTooEarly()
    with pytest.raises(AttributeError, match="_fields_ is final"):
        UsedTooEarly._fields_ = [("value", ctypes.c_int)]


def test_structure_subclass_appends_its_fields_after_base_layout():
    """继承保留 base fields；subclass fields 继续遵守 ABI alignment。"""

    packet = Packet(kind=3, length=500)

    assert packet.kind == 3
    assert packet.length == 500
    assert Packet.length.offset >= ctypes.sizeof(Header)


def test_tuple_swap_of_nested_wrappers_does_not_make_value_snapshots():
    """RHS wrapper 都 alias pair；第一次字段复制后，第二个 RHS 所见内容已经变化。"""

    pair = Pair(Point(1, 2), Point(3, 4))
    pair.first, pair.second = pair.second, pair.first

    assert (pair.first.x, pair.first.y) == (3, 4)
    assert (pair.second.x, pair.second.y) == (3, 4)

    safe = Pair(Point(1, 2), Point(3, 4))
    first_snapshot = Point(safe.first.x, safe.first.y)
    second_snapshot = Point(safe.second.x, safe.second.y)
    safe.first, safe.second = second_snapshot, first_snapshot
    assert (safe.first.x, safe.second.x) == (3, 1)


def test_endian_base_classes_produce_explicit_wire_byte_order():
    """bytes(instance) 暴露 structure storage；native sys.byteorder 不影响显式 endian。"""

    network = NetworkWord(value=0x1234)
    little = LittleWord(value=0x1234)

    assert bytes(network) == b"\x12\x34"
    assert bytes(little) == b"\x34\x12"
    native = little if sys.byteorder == "little" else network
    assert int.from_bytes(bytes(native), sys.byteorder) == 0x1234


def test_non_native_endian_structure_rejects_pointer_fields():
    """pointer 自身的 byte order 没有可移植转换规则，因此 class 创建即失败。"""

    with pytest.raises(TypeError):
        class InvalidNetworkRecord(ctypes.BigEndianStructure):
            _fields_ = [("pointer", ctypes.POINTER(ctypes.c_int))]
