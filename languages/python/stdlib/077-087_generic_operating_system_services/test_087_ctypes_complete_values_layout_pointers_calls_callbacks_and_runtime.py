"""087｜``ctypes`` scalar、pointer-like string types 与 owned buffers。

ctypes scalar 用 ``value`` 在 Python/C 表示间转换；固定宽整数按 C 宽度截断，不做 Python
整数的溢出保护。``c_char_p`` 只保存地址且适合只读 NUL-terminated bytes，需原地修改时
应使用 ``create_string_buffer`` 拥有可写存储，并明确是否为末尾 NUL 预留空间。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.ctypes._SimpleCData python.ctypes.scalar-value
# polyglot-covers: python.ctypes.c_bool python.ctypes.c_int
# polyglot-covers: python.ctypes.c_byte python.ctypes.c_ubyte
# polyglot-covers: python.ctypes.c_double python.ctypes.c_char
# polyglot-covers: python.ctypes.c_wchar python.ctypes.c_void_p
# polyglot-covers: python.ctypes.c_char_p python.ctypes.c_wchar_p
# polyglot-covers: python.ctypes.c_char_p-value-identity
# polyglot-covers: python.ctypes.py_object
# polyglot-covers: python.ctypes.create_string_buffer
# polyglot-covers: python.ctypes.string-buffer-raw-vs-value
# polyglot-covers: python.ctypes.string-buffer-nul-capacity-trap
# polyglot-covers: python.ctypes.create_unicode_buffer



import ctypes
import pytest
import sys
import ctypes.util
import errno
import os
import queue
import threading
from ctypes import wintypes

def test_scalar_value_converts_between_python_and_c_representations():
    """无参构造零初始化；value 赋值立即按目标 C type 转换。"""

    integer = ctypes.c_int()
    floating = ctypes.c_double(1.25)
    truth = ctypes.c_bool(7)
    character = ctypes.c_char(b"A")
    wide_character = ctypes.c_wchar("汉")

    assert integer.value == 0
    integer.value = -12
    assert integer.value == -12
    assert floating.value == 1.25
    assert truth.value is True
    assert character.value == b"A"
    assert wide_character.value == "汉"


def test_fixed_width_integer_construction_wraps_like_a_c_conversion():
    """ctypes 不替调用方做范围校验；协议字段应在构造前显式检查上界。"""

    assert ctypes.c_ubyte(-1).value == 255
    assert ctypes.c_ubyte(256).value == 0
    assert ctypes.c_byte(255).value == -1


def test_pointer_like_scalars_use_none_for_null_and_do_not_own_mutable_text():
    """c_char_p.value 每次解引用生成等值 bytes，不保证 Python object identity。"""

    raw = b"a sufficiently long byte sequence"
    text_pointer = ctypes.c_char_p(raw)
    first = text_pointer.value
    second = text_pointer.value

    assert first == second == raw
    assert first is not second
    text_pointer.value = None
    assert text_pointer.value is None

    wide_pointer = ctypes.c_wchar_p("hello")
    address = ctypes.c_void_p(0x1234)
    assert wide_pointer.value == "hello"
    assert address.value == 0x1234
    address.value = None
    assert address.value is None


def test_py_object_keeps_and_returns_the_original_python_reference():
    """py_object 用于 C API 的 PyObject*；value 不是序列化副本。"""

    payload = {"items": [1, 2]}
    holder = ctypes.py_object(payload)

    assert holder.value is payload
    holder.value["items"].append(3)
    assert payload == {"items": [1, 2, 3]}


def test_string_buffer_owns_mutable_nul_terminated_storage():
    """省略 size 时自动分配 len(init)+1；raw 包含容量，value 截到首个 NUL。"""

    buffer = ctypes.create_string_buffer(b"abc")

    assert len(buffer) == 4
    assert buffer.raw == b"abc\x00"
    assert buffer.value == b"abc"
    buffer[1] = b"Z"
    assert buffer.value == b"aZc"

    buffer.raw = b"x\x00yz"
    assert buffer.raw == b"x\x00yz"
    assert buffer.value == b"x"


def test_explicit_exact_buffer_size_has_no_trailing_nul():
    """size == len(init) 被允许，但传给期待 C string 的函数可能越界读取。"""

    exact = ctypes.create_string_buffer(b"abc", 3)
    terminated = ctypes.create_string_buffer(b"abc", 4)

    assert exact.raw == b"abc"
    assert terminated.raw == b"abc\x00"


def test_unicode_buffer_stores_mutable_wchar_array():
    """容量按 wchar_t 元素计数，不是 UTF-8 byte 数。"""

    buffer = ctypes.create_unicode_buffer("猫", 4)

    assert len(buffer) == 4
    assert buffer.value == "猫"
    buffer[1] = "狗"
    assert buffer.value == "猫狗"
    buffer[2] = "\x00"
    assert buffer.value == "猫狗"


# ``ctypes`` array、typed pointer、``byref`` 与 ``cast`` aliasing。
#
# ``T * n`` 创建固定长度 array type；``POINTER(T)`` 创建并缓存 typed pointer type。
# pointer/contents/byref/cast 都可能让多个 Python wrapper 指向同一块 C 内存，不会复制值。
# pointer 没有长度元数据，越界读写可能崩溃，案例只访问已知有效范围。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# ``ctypes.Structure``/``Union`` layout、packing、anonymous 与 bit fields。
#
# ``_fields_`` 的顺序决定 C layout，descriptor 暴露 offset/size；``_pack_`` 必须在 fields
# 之前声明。Union 的所有字段共享地址，解释哪一个字段有效由外部 tag/protocol 决定。
# bit field 顺序与 ABI 有关，含 bit field 的结构不应按值传给 foreign function。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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



class LayoutPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]


class Rectangle(ctypes.Structure):
    _fields_ = [("upper_left", LayoutPoint), ("lower_right", LayoutPoint)]


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

    point = LayoutPoint(3, y=4)
    point.label = "debug-only"
    rectangle = Rectangle(point, LayoutPoint(8, 9))

    assert (point.x, point.y) == (3, 4)
    assert point.label == "debug-only"
    assert (rectangle.upper_left.x, rectangle.lower_right.y) == (3, 9)
    assert LayoutPoint.x.offset == 0
    assert LayoutPoint.y.offset == ctypes.sizeof(ctypes.c_int)
    assert LayoutPoint.x.size == ctypes.sizeof(ctypes.c_int)


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


# ``ctypes`` incomplete recursive types、endian structures 与 wrapper alias trap。
#
# 递归结构要先声明空 class，再赋 ``_fields_``，这样才能创建指向自身的 POINTER type。
# nested structure 属性返回引用父 buffer 的 wrapper，不是独立副本，因此直接 tuple-swap
# 会因第一次写入改变第二个 wrapper 所见内存。跨字节序结构则禁止 pointer fields。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.incomplete-Structure
# polyglot-covers: python.ctypes.recursive-Structure python.ctypes.self-pointer
# polyglot-covers: python.ctypes.Structure-fields-final
# polyglot-covers: python.ctypes.structure-inheritance
# polyglot-covers: python.ctypes.nested-structure-wrapper-alias
# polyglot-covers: python.ctypes.structure-tuple-swap-trap
# polyglot-covers: python.ctypes.BigEndianStructure
# polyglot-covers: python.ctypes.LittleEndianStructure
# polyglot-covers: python.ctypes.endian-structure-pointer-prohibition




class Cell(ctypes.Structure):
    pass


Cell._fields_ = [("value", ctypes.c_int), ("next", ctypes.POINTER(Cell))]


class RecursivePoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]


class Pair(ctypes.Structure):
    _fields_ = [("first", RecursivePoint), ("second", RecursivePoint)]


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

    pair = Pair(RecursivePoint(1, 2), RecursivePoint(3, 4))
    pair.first, pair.second = pair.second, pair.first

    assert (pair.first.x, pair.first.y) == (3, 4)
    assert (pair.second.x, pair.second.y) == (3, 4)

    safe = Pair(RecursivePoint(1, 2), RecursivePoint(3, 4))
    first_snapshot = RecursivePoint(safe.first.x, safe.first.y)
    second_snapshot = RecursivePoint(safe.second.x, safe.second.y)
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


# ``ctypes`` dynamic library loading、foreign function 与 signature。
#
# ``CDLL`` 加载采用 cdecl calling convention 的共享库；``CDLL(None)`` 表示当前进程的
# 全局符号空间。函数默认返回 ``c_int``，实际调用前应声明 ``restype`` 和 ``argtypes``，
# 否则 pointer-sized 返回值可能被截断，错误的参数也可能直到 native code 中才暴露。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.CDLL python.ctypes.CDLL-none
# polyglot-covers: python.ctypes.CDLL-name python.ctypes.CDLL-handle
# polyglot-covers: python.ctypes.cdll python.ctypes.LibraryLoader.LoadLibrary
# polyglot-covers: python.ctypes.shared-library-load-error
# polyglot-covers: python.ctypes.foreign-function-attribute-cache
# polyglot-covers: python.ctypes.foreign-function-index-fresh-wrapper
# polyglot-covers: python.ctypes.foreign-function-default-restype
# polyglot-covers: python.ctypes.foreign-function-restype
# polyglot-covers: python.ctypes.foreign-function-argtypes
# polyglot-covers: python.ctypes.ArgumentError python.ctypes.c-string-nul-semantics




def _load_functions_c_library():
    """Docker 目标是 POSIX；极简平台若找不到 libc 名称则明确跳过依赖符号的案例。"""

    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("ctypes.util.find_library('c') 未找到 C runtime")
    return name, ctypes.CDLL(name)


def test_cdll_loads_named_library_and_none_opens_current_process():
    """handle 是 native loader handle；只检查其结构，不依赖平台具体数值。"""

    name, library = _load_functions_c_library()
    current_process = ctypes.CDLL(None)
    loaded_by_factory = ctypes.cdll.LoadLibrary(name)

    assert library._name == name
    assert isinstance(library._handle, int)
    assert current_process._name is None
    assert isinstance(current_process._handle, int)
    assert isinstance(loaded_by_factory, ctypes.CDLL)


def test_missing_shared_library_raises_oserror(tmp_path):
    """加载失败来自操作系统 dynamic loader，不会返回 false-like library object。"""

    missing = tmp_path / "lib_polyglot_definitely_missing.so"

    with pytest.raises(OSError):
        ctypes.CDLL(str(missing))


def test_function_attribute_lookup_is_cached_but_index_lookup_is_fresh():
    """fresh wrapper 适合为同一 native symbol 配置互不干扰的不同 signature。"""

    _, library = _load_functions_c_library()

    assert library.strlen is library.strlen
    assert library["strlen"] is not library["strlen"]


def test_declared_strlen_signature_converts_bytes_and_rejects_text():
    """c_char_p 接收 bytes；C strlen 在首个 NUL 停止，而 Python len 会计入后缀。"""

    _, library = _load_functions_c_library()
    strlen = library["strlen"]

    assert strlen.restype is ctypes.c_int
    assert strlen.argtypes is None

    strlen.restype = ctypes.c_size_t
    strlen.argtypes = [ctypes.c_char_p]

    assert strlen(b"hello") == 5
    assert strlen(b"ab\x00ignored") == 2
    with pytest.raises(ctypes.ArgumentError):
        strlen("hello")


# ``ctypes`` variadic calls、``CFUNCTYPE`` prototype 与 ``paramflags``。
#
# variadic C function 仍应为固定参数声明 ``argtypes``，额外参数则显式包装成 ctypes object；
# 这既记录 ABI 意图，也满足部分平台对 varargs register convention 的要求。Function
# prototype 还能把 symbol、library 与 paramflags 组合成支持命名参数和默认值的 callable。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.variadic-functions
# polyglot-covers: python.ctypes.variadic-fixed-argtypes
# polyglot-covers: python.ctypes.variadic-explicit-extra-arguments
# polyglot-covers: python.ctypes.CFUNCTYPE python.ctypes.cdecl-prototype
# polyglot-covers: python.ctypes.function-prototype-symbol-binding
# polyglot-covers: python.ctypes.paramflags python.ctypes.paramflags-input
# polyglot-covers: python.ctypes.paramflags-named-arguments
# polyglot-covers: python.ctypes.paramflags-default-value




def _load_variadic_c_library():
    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")
    return ctypes.CDLL(name)


def test_snprintf_declares_fixed_arguments_and_wraps_variadic_values():
    """额外的 int/string 也显式使用 c_int/c_char_p，避免依赖不完整的自动转换。"""

    library = _load_variadic_c_library()
    snprintf = library["snprintf"]
    snprintf.restype = ctypes.c_int
    snprintf.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_size_t,
        ctypes.c_char_p,
    ]
    output = ctypes.create_string_buffer(64)

    required = snprintf(
        output,
        len(output),
        b"value=%d text=%s",
        ctypes.c_int(7),
        ctypes.c_char_p(b"ok"),
    )

    assert output.value == b"value=7 text=ok"
    assert required == len(output.value)


def test_cfunctype_binds_symbol_with_named_input_parameters():
    """param flag 1 表示 input；名称使 positional 与 keyword 两种调用都清晰。"""

    library = _load_variadic_c_library()
    Compare = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p)
    compare = Compare(
        ("strcmp", library),
        ((1, "left"), (1, "right")),
    )

    assert compare(b"same", b"same") == 0
    assert compare(left=b"a", right=b"b") < 0
    assert compare(right=b"a", left=b"b") > 0


def test_paramflags_can_supply_default_for_an_input_parameter():
    """第三项是默认值；省略 right 时并不意味着给 C 传入未初始化内存。"""

    library = _load_variadic_c_library()
    Compare = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p)
    compare_to_default = Compare(
        ("strcmp", library),
        ((1, "left"), (1, "right", b"baseline")),
    )

    assert compare_to_default(b"baseline") == 0
    assert compare_to_default(left=b"after") < 0


# ``ctypes`` callbacks、``CFUNCTYPE`` lifetime 与 C ``qsort`` workflow。
#
# 用 Python callable 构造 function pointer 后，C 只保存裸地址；只要 native code 仍可能
# 回调，就必须在 Python 侧保留强引用。callback 抛出的异常不能像普通调用那样穿过 C
# stack 传播，因此 callback 边界应捕获错误并返回协议约定的状态值。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.CFUNCTYPE-callback
# polyglot-covers: python.ctypes.callback-function-pointer
# polyglot-covers: python.ctypes.callback-direct-call
# polyglot-covers: python.ctypes.callback-argument-conversion
# polyglot-covers: python.ctypes.callback-return-conversion
# polyglot-covers: python.ctypes.callback-lifetime-trap
# polyglot-covers: python.ctypes.callback-exception-boundary
# polyglot-covers: python.ctypes.callback-in-Structure
# polyglot-covers: python.ctypes.qsort-workflow
# polyglot-covers: python.ctypes.PYFUNCTYPE




def _load_callback_c_library():
    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")
    return ctypes.CDLL(name)


def test_callback_converts_arguments_and_return_value_on_direct_call():
    """装饰器把 Python function 替换为持有 C-callable trampoline 的 callback object。"""

    BinaryOperation = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int)

    @BinaryOperation
    def add(left, right):
        return left + right

    assert add(20, 22) == 42
    assert type(add) is BinaryOperation


def test_qsort_calls_python_comparator_and_mutates_ctypes_array_in_place():
    """comparator 在 qsort 返回前保持为局部强引用；不要临时构造后交给长期持有者。"""

    library = _load_callback_c_library()
    Comparator = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    )
    seen = []

    @Comparator
    def compare(left, right):
        left_value = left[0]
        right_value = right[0]
        seen.append((left_value, right_value))
        return (left_value > right_value) - (left_value < right_value)

    qsort = library["qsort"]
    qsort.restype = None
    qsort.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_size_t,
        Comparator,
    ]
    values = (ctypes.c_int * 5)(5, 1, 4, 2, 3)

    qsort(values, len(values), ctypes.sizeof(ctypes.c_int), compare)

    assert values[:] == [1, 2, 3, 4, 5]
    assert seen


def test_callback_can_be_stored_as_a_structure_function_pointer_field():
    """Structure 持有 callback wrapper，因此 record 活着时 trampoline 也保持可达。"""

    Transform = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)

    class HandlerRecord(ctypes.Structure):
        _fields_ = [("transform", Transform)]

    callback = Transform(lambda value: value * 2)
    record = HandlerRecord(callback)

    assert record.transform(21) == 42


def test_pyfunctype_keeps_the_gil_for_python_c_api_style_callbacks():
    """PYFUNCTYPE 的 calling convention 类似 CFUNCTYPE，但调用期间不释放 GIL。"""

    Identity = ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.py_object)
    identity = Identity(lambda value: value)
    payload = {"answer": 42}

    assert identity(payload) is payload


# ``ctypes`` ``_as_parameter_``、``from_param`` 与 ``errcheck`` adapters。
#
# ``argtypes`` 的每一项不必是 ctypes type：只要提供 ``from_param``，就能在进入 native
# code 前集中验证 domain object。Instance 的 ``_as_parameter_`` 是更轻量的单值适配。
# ``errcheck`` 则在 restype 转换后统一解释 status/pointer 并映射成 Python 结果或异常。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes._as_parameter_
# polyglot-covers: python.ctypes.dynamic-as-parameter-property
# polyglot-covers: python.ctypes.from_param python.ctypes.custom-argtypes-adapter
# polyglot-covers: python.ctypes.from-param-validation
# polyglot-covers: python.ctypes.from-param-ArgumentError
# polyglot-covers: python.ctypes.errcheck
# polyglot-covers: python.ctypes.errcheck-result-function-arguments
# polyglot-covers: python.ctypes.errcheck-pointer-to-python-result
# polyglot-covers: python.ctypes.errcheck-error-mapping




def _load_adapter_c_library():
    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")
    return ctypes.CDLL(name)


def test_as_parameter_adapts_domain_object_at_each_call():
    """property 可反映对象最新状态；ctypes 不会缓存第一次转换所得的 c_int。"""

    class SignedValue:
        def __init__(self, value):
            self.value = value

        @property
        def _as_parameter_(self):
            return ctypes.c_int(self.value)

    absolute = _load_adapter_c_library()["abs"]
    absolute.restype = ctypes.c_int
    absolute.argtypes = [ctypes.c_int]
    value = SignedValue(-7)

    assert absolute(value) == 7
    value.value = -11
    assert absolute(value) == 11


def test_custom_from_param_performs_validation_and_conversion():
    """converter 的异常由调用层包装为 ArgumentError，避免无效值到达 C。"""

    class BoundedInteger:
        @classmethod
        def from_param(cls, value):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError("expected a non-bool int")
            if not -100 <= value <= 100:
                raise ValueError("value outside teaching range")
            return ctypes.c_int(value)

    absolute = _load_adapter_c_library()["abs"]
    absolute.restype = ctypes.c_int
    absolute.argtypes = [BoundedInteger]

    assert absolute(-12) == 12
    with pytest.raises(ctypes.ArgumentError):
        absolute(True)
    with pytest.raises(ctypes.ArgumentError):
        absolute(101)


def test_errcheck_turns_pointer_result_into_bytes_or_domain_error():
    """strchr 返回指向原 bytes 中命中位置的地址；string_at 从该地址读到后续 NUL。"""

    strchr = _load_adapter_c_library()["strchr"]
    strchr.restype = ctypes.c_void_p
    strchr.argtypes = [ctypes.c_char_p, ctypes.c_int]
    observations = []

    def suffix_or_error(result, function, arguments):
        observations.append((function is strchr, arguments))
        if result is None:
            raise LookupError("character not found")
        return ctypes.string_at(result)

    strchr.errcheck = suffix_or_error

    assert strchr(b"abcdef", ord("c")) == b"cdef"
    assert observations == [(True, (b"abcdef", ord("c")))]
    with pytest.raises(LookupError, match="character not found"):
        strchr(b"abcdef", ord("z"))


# ``ctypes`` address/size/alignment、raw memory utilities 与 ``resize``。
#
# ``addressof``/``string_at``/``memmove`` 等 API 直接操作 native address，不携带 ownership
# 或边界信息；案例只使用仍存活的 ctypes-owned buffer 和已知长度。``resize`` 可扩大 backing
# store，却不会改变原 array type 的 ``_length_``，所以新增空间仍需通过正确 pointer view 访问。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.addressof python.ctypes.sizeof
# polyglot-covers: python.ctypes.alignment python.ctypes.native-address
# polyglot-covers: python.ctypes.memmove python.ctypes.memset
# polyglot-covers: python.ctypes.string_at python.ctypes.string_at-explicit-size
# polyglot-covers: python.ctypes.wstring_at
# polyglot-covers: python.ctypes.resize python.ctypes.resize-grow
# polyglot-covers: python.ctypes.resize-type-length-trap
# polyglot-covers: python.ctypes.resize-smaller-error




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


# ``ctypes`` ``use_errno``、private errno copy 与 thread-local state。
#
# 声明 ``use_errno=True`` 后，ctypes 会在 foreign call 前后与真实 C errno 交换一份
# thread-local copy，调用方再用 ``get_errno`` 读取。这避免另一个 C call 提前覆盖错误码，
# 但仍必须紧跟返回值协议判断；errno 非零本身不代表本次调用失败。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.get_errno python.ctypes.set_errno
# polyglot-covers: python.ctypes.set-errno-returns-previous
# polyglot-covers: python.ctypes.errno-thread-local
# polyglot-covers: python.ctypes.CDLL-use_errno
# polyglot-covers: python.ctypes.foreign-call-errno-capture
# polyglot-covers: python.ctypes.errno-return-value-first
# polyglot-covers: python.ctypes.get_last_error-platform-availability
# polyglot-covers: python.ctypes.set_last_error-platform-availability




def test_set_errno_returns_previous_value_and_state_is_thread_local():
    """worker 修改自己的 private copy，不会覆盖 main thread 已设置的 EINVAL。"""

    original = ctypes.get_errno()
    result_queue = queue.Queue()

    def worker():
        initial = ctypes.get_errno()
        previous = ctypes.set_errno(errno.EBUSY)
        result_queue.put((initial, previous, ctypes.get_errno()))

    try:
        assert ctypes.set_errno(errno.EINVAL) == original
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        initial, previous, current = result_queue.get_nowait()
        assert (initial, previous, current) == (0, 0, errno.EBUSY)
        assert ctypes.get_errno() == errno.EINVAL
    finally:
        ctypes.set_errno(original)


@pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX libc close")
def test_use_errno_captures_close_failure_immediately_after_foreign_call():
    """-1 先表明失败，EBADF 才解释原因；案例只关闭必然无效的负 fd。"""

    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")

    library = ctypes.CDLL(name, use_errno=True)
    close = library["close"]
    close.restype = ctypes.c_int
    close.argtypes = [ctypes.c_int]
    original = ctypes.get_errno()

    try:
        ctypes.set_errno(0)
        result = close(-1)

        assert result == -1
        assert ctypes.get_errno() == errno.EBADF
    finally:
        ctypes.set_errno(original)


def test_windows_last_error_helpers_are_exposed_only_on_windows():
    """不要在跨平台 module import 阶段无条件引用仅 Windows 提供的 helper。"""

    expected = os.name == "nt"

    assert hasattr(ctypes, "get_last_error") is expected
    assert hasattr(ctypes, "set_last_error") is expected


# ``ctypes.pythonapi``、``PyDLL``、Python C API 与 ``in_dll``。
#
# ``pythonapi`` 是当前解释器的 ``PyDLL``：foreign call 期间保留 GIL，并在返回后检查
# Python error indicator。C API signature 默认仍是 c_int，因此每次使用前必须声明正确
# restype/argtypes。``in_dll`` 可把 exported variable 映射为共享 native storage，应谨慎只读。
#
# 这些案例面向 CPython 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.pythonapi python.ctypes.PyDLL
# polyglot-covers: python.ctypes.PyDLL-gil
# polyglot-covers: python.ctypes.PyDLL-python-error-check
# polyglot-covers: python.ctypes.python-c-api-signature
# polyglot-covers: python.ctypes.c_char_p-restype
# polyglot-covers: python.ctypes.py_object-restype
# polyglot-covers: python.ctypes.PyErr_SetString
# polyglot-covers: python.ctypes.in_dll python.ctypes.exported-variable-view
# polyglot-covers: python.ctypes.Py_OptimizeFlag




_section_217_pytestmark = pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="pythonapi symbol 案例锁定 CPython 3.10",
)


def _call_with_temporary_signature(function, restype, argtypes, *arguments):
    """pythonapi attribute lookup 会缓存 wrapper，因此恢复配置以避免跨测试泄漏。"""

    old_restype = function.restype
    old_argtypes = function.argtypes
    try:
        function.restype = restype
        function.argtypes = argtypes
        return function(*arguments)
    finally:
        function.restype = old_restype
        function.argtypes = old_argtypes


@_section_217_pytestmark
def test_pythonapi_is_pydll_and_get_version_returns_c_string():
    """c_char_p restype 自动把 char* 指向的 NUL-terminated 内容转换为 bytes。"""

    assert isinstance(ctypes.pythonapi, ctypes.PyDLL)

    version = _call_with_temporary_signature(
        ctypes.pythonapi.Py_GetVersion,
        ctypes.c_char_p,
        [],
    )

    assert version.startswith(f"{sys.version_info.major}.{sys.version_info.minor}".encode())


@_section_217_pytestmark
def test_py_object_restype_turns_new_python_object_pointer_into_object():
    """PyLong_FromLong 返回 PyObject* new reference；py_object 暴露为普通 Python int。"""

    result = _call_with_temporary_signature(
        ctypes.pythonapi.PyLong_FromLong,
        ctypes.py_object,
        [ctypes.c_long],
        123456,
    )

    assert result == 123456
    assert type(result) is int


@_section_217_pytestmark
def test_pydll_raises_when_c_api_leaves_python_error_indicator_set():
    """PyErr_SetString 的 void 返回并非成功；PyDLL 检查 indicator 后重抛对应异常。"""

    with pytest.raises(ValueError, match="foreign failure"):
        _call_with_temporary_signature(
            ctypes.pythonapi.PyErr_SetString,
            None,
            [ctypes.py_object, ctypes.c_char_p],
            ValueError,
            b"foreign failure",
        )


@_section_217_pytestmark
def test_in_dll_reads_exported_interpreter_configuration_variable():
    """view 指向解释器真实 global；示例只读，修改可能破坏当前 process invariants。"""

    optimize_flag = ctypes.c_int.in_dll(ctypes.pythonapi, "Py_OptimizeFlag")

    assert optimize_flag.value == sys.flags.optimize


# ``ctypes.util`` library discovery、loader objects 与 Windows type surface。
#
# ``find_library`` 返回可交给 loader 的平台相关名称，不保证是绝对路径。LibraryLoader
# 只是按指定 DLL type 建 object 的便利 facade；calling convention 仍由 CDLL/PyDLL/
# WinDLL 等 class 决定。``ctypes.wintypes`` 可导入 type declarations，但 Windows ABI
# 调用与 WinDLL/OleDLL loaders 只应在 Windows 分支使用。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.ctypes.util python.ctypes.util.find_library
# polyglot-covers: python.ctypes.find-library-platform-name
# polyglot-covers: python.ctypes.LibraryLoader
# polyglot-covers: python.ctypes.LibraryLoader-index
# polyglot-covers: python.ctypes.predefined-library-loaders
# polyglot-covers: python.ctypes.pydll-loader
# polyglot-covers: python.ctypes.DEFAULT_MODE python.ctypes.RTLD_GLOBAL
# polyglot-covers: python.ctypes.RTLD_LOCAL
# polyglot-covers: python.ctypes.wintypes python.ctypes.wintypes.POINT
# polyglot-covers: python.ctypes.wintypes.RECT python.ctypes.wintypes.HANDLE
# polyglot-covers: python.ctypes.WinDLL-platform-availability
# polyglot-covers: python.ctypes.OleDLL-platform-availability
# polyglot-covers: python.ctypes.windll-platform-availability
# polyglot-covers: python.ctypes.oledll-platform-availability




def _c_library_name():
    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")
    return name


def test_find_library_result_is_loader_input_not_required_absolute_path():
    """只要求结果可加载；Linux 常见 soname、macOS path 与 Windows 名称格式都不同。"""

    name = _c_library_name()
    library = ctypes.CDLL(name, mode=ctypes.DEFAULT_MODE)

    assert isinstance(name, str)
    assert name
    assert isinstance(library, ctypes.CDLL)
    assert ctypes.util.find_library("polyglot_library_that_cannot_exist_7f3a") is None


def test_libraryloader_supports_explicit_load_and_index_syntax():
    """两次访问创建两个 Python library wrappers；native loader 可在底层复用 handle。"""

    name = _c_library_name()
    loader = ctypes.LibraryLoader(ctypes.CDLL)
    explicit = loader.LoadLibrary(name)
    indexed = loader[name]

    assert isinstance(explicit, ctypes.CDLL)
    assert isinstance(indexed, ctypes.CDLL)
    assert explicit is not indexed
    assert isinstance(ctypes.cdll, ctypes.LibraryLoader)
    assert isinstance(ctypes.pydll, ctypes.LibraryLoader)


def test_loader_mode_constants_are_integer_platform_configuration():
    """常量值由平台决定；跨平台代码不应假设 RTLD_GLOBAL 的具体 bit pattern。"""

    assert isinstance(ctypes.DEFAULT_MODE, int)
    assert isinstance(ctypes.RTLD_GLOBAL, int)
    assert isinstance(ctypes.RTLD_LOCAL, int)


def test_wintypes_structures_preserve_declared_field_workflow():
    """可在任意平台学习 shape；只有 Windows 上的 size/calling convention 才是目标 ABI。"""

    point = wintypes.POINT(x=3, y=4)
    rectangle = wintypes.RECT(left=1, top=2, right=11, bottom=22)
    null_handle = wintypes.HANDLE()

    assert (point.x, point.y) == (3, 4)
    assert (rectangle.right - rectangle.left) == 10
    assert (rectangle.bottom - rectangle.top) == 20
    assert null_handle.value is None


def test_windows_calling_convention_loaders_are_platform_conditional():
    """在 module scope 无条件引用 WinDLL/windll 会让 POSIX import 直接失败。"""

    expected = os.name == "nt"

    for name in ("WinDLL", "OleDLL", "windll", "oledll"):
        assert hasattr(ctypes, name) is expected
