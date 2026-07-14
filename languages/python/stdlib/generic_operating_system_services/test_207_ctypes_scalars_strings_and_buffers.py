"""207｜``ctypes`` scalar、pointer-like string types 与 owned buffers。

ctypes scalar 用 ``value`` 在 Python/C 表示间转换；固定宽整数按 C 宽度截断，不做 Python
整数的溢出保护。``c_char_p`` 只保存地址且适合只读 NUL-terminated bytes，需原地修改时
应使用 ``create_string_buffer`` 拥有可写存储，并明确是否为末尾 NUL 预留空间。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
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
