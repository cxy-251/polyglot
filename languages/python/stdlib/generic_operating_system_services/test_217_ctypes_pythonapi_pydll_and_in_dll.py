"""217｜``ctypes.pythonapi``、``PyDLL``、Python C API 与 ``in_dll``。

``pythonapi`` 是当前解释器的 ``PyDLL``：foreign call 期间保留 GIL，并在返回后检查
Python error indicator。C API signature 默认仍是 c_int，因此每次使用前必须声明正确
restype/argtypes。``in_dll`` 可把 exported variable 映射为共享 native storage，应谨慎只读。

这些案例面向 CPython 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.pythonapi python.ctypes.PyDLL
# polyglot-covers: python.ctypes.PyDLL-gil
# polyglot-covers: python.ctypes.PyDLL-python-error-check
# polyglot-covers: python.ctypes.python-c-api-signature
# polyglot-covers: python.ctypes.c_char_p-restype
# polyglot-covers: python.ctypes.py_object-restype
# polyglot-covers: python.ctypes.PyErr_SetString
# polyglot-covers: python.ctypes.in_dll python.ctypes.exported-variable-view
# polyglot-covers: python.ctypes.Py_OptimizeFlag

import ctypes
import sys

import pytest


pytestmark = pytest.mark.skipif(
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


def test_pythonapi_is_pydll_and_get_version_returns_c_string():
    """c_char_p restype 自动把 char* 指向的 NUL-terminated 内容转换为 bytes。"""

    assert isinstance(ctypes.pythonapi, ctypes.PyDLL)

    version = _call_with_temporary_signature(
        ctypes.pythonapi.Py_GetVersion,
        ctypes.c_char_p,
        [],
    )

    assert version.startswith(f"{sys.version_info.major}.{sys.version_info.minor}".encode())


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


def test_in_dll_reads_exported_interpreter_configuration_variable():
    """view 指向解释器真实 global；示例只读，修改可能破坏当前 process invariants。"""

    optimize_flag = ctypes.c_int.in_dll(ctypes.pythonapi, "Py_OptimizeFlag")

    assert optimize_flag.value == sys.flags.optimize
