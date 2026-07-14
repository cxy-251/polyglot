"""212｜``ctypes`` variadic calls、``CFUNCTYPE`` prototype 与 ``paramflags``。

variadic C function 仍应为固定参数声明 ``argtypes``，额外参数则显式包装成 ctypes object；
这既记录 ABI 意图，也满足部分平台对 varargs register convention 的要求。Function
prototype 还能把 symbol、library 与 paramflags 组合成支持命名参数和默认值的 callable。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.variadic-functions
# polyglot-covers: python.ctypes.variadic-fixed-argtypes
# polyglot-covers: python.ctypes.variadic-explicit-extra-arguments
# polyglot-covers: python.ctypes.CFUNCTYPE python.ctypes.cdecl-prototype
# polyglot-covers: python.ctypes.function-prototype-symbol-binding
# polyglot-covers: python.ctypes.paramflags python.ctypes.paramflags-input
# polyglot-covers: python.ctypes.paramflags-named-arguments
# polyglot-covers: python.ctypes.paramflags-default-value

import ctypes
import ctypes.util

import pytest


def _load_c_library():
    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")
    return ctypes.CDLL(name)


def test_snprintf_declares_fixed_arguments_and_wraps_variadic_values():
    """额外的 int/string 也显式使用 c_int/c_char_p，避免依赖不完整的自动转换。"""

    library = _load_c_library()
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

    library = _load_c_library()
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

    library = _load_c_library()
    Compare = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p)
    compare_to_default = Compare(
        ("strcmp", library),
        ((1, "left"), (1, "right", b"baseline")),
    )

    assert compare_to_default(b"baseline") == 0
    assert compare_to_default(left=b"after") < 0
