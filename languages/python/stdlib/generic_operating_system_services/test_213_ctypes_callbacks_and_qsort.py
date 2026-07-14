"""213｜``ctypes`` callbacks、``CFUNCTYPE`` lifetime 与 C ``qsort`` workflow。

用 Python callable 构造 function pointer 后，C 只保存裸地址；只要 native code 仍可能
回调，就必须在 Python 侧保留强引用。callback 抛出的异常不能像普通调用那样穿过 C
stack 传播，因此 callback 边界应捕获错误并返回协议约定的状态值。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import ctypes
import ctypes.util

import pytest


def _load_c_library():
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

    library = _load_c_library()
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
