"""214｜``ctypes`` ``_as_parameter_``、``from_param`` 与 ``errcheck`` adapters。

``argtypes`` 的每一项不必是 ctypes type：只要提供 ``from_param``，就能在进入 native
code 前集中验证 domain object。Instance 的 ``_as_parameter_`` 是更轻量的单值适配。
``errcheck`` 则在 restype 转换后统一解释 status/pointer 并映射成 Python 结果或异常。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes._as_parameter_
# polyglot-covers: python.ctypes.dynamic-as-parameter-property
# polyglot-covers: python.ctypes.from_param python.ctypes.custom-argtypes-adapter
# polyglot-covers: python.ctypes.from-param-validation
# polyglot-covers: python.ctypes.from-param-ArgumentError
# polyglot-covers: python.ctypes.errcheck
# polyglot-covers: python.ctypes.errcheck-result-function-arguments
# polyglot-covers: python.ctypes.errcheck-pointer-to-python-result
# polyglot-covers: python.ctypes.errcheck-error-mapping

import ctypes
import ctypes.util

import pytest


def _load_c_library():
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

    absolute = _load_c_library()["abs"]
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

    absolute = _load_c_library()["abs"]
    absolute.restype = ctypes.c_int
    absolute.argtypes = [BoundedInteger]

    assert absolute(-12) == 12
    with pytest.raises(ctypes.ArgumentError):
        absolute(True)
    with pytest.raises(ctypes.ArgumentError):
        absolute(101)


def test_errcheck_turns_pointer_result_into_bytes_or_domain_error():
    """strchr 返回指向原 bytes 中命中位置的地址；string_at 从该地址读到后续 NUL。"""

    strchr = _load_c_library()["strchr"]
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
