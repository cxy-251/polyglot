"""238｜``Value``/``Array``、``sharedctypes`` wrappers 与 compound-operation trap。

Synchronized wrapper 只在单次 attribute/index access 时自动加锁；``value += 1`` 是读改写
三步，仍须显式 ``get_lock`` 包住整体。RawValue/RawArray 没有 lock。shared memory 中不可
存放供另一 process 解引用的 native pointer，因为每个 process address space 不同。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Value python.multiprocessing.Array
# polyglot-covers: python.multiprocessing.synchronized-wrapper
# polyglot-covers: python.multiprocessing.get_obj python.multiprocessing.get_lock
# polyglot-covers: python.multiprocessing.Value-compound-operation-not-atomic
# polyglot-covers: python.multiprocessing.Value-explicit-lock-atomic-update
# polyglot-covers: python.multiprocessing.Value-lock-false
# polyglot-covers: python.multiprocessing.Array-char-value-raw
# polyglot-covers: python.multiprocessing.sharedctypes
# polyglot-covers: python.multiprocessing.sharedctypes.RawValue
# polyglot-covers: python.multiprocessing.sharedctypes.RawArray
# polyglot-covers: python.multiprocessing.sharedctypes.Value
# polyglot-covers: python.multiprocessing.sharedctypes.Array
# polyglot-covers: python.multiprocessing.sharedctypes.copy
# polyglot-covers: python.multiprocessing.sharedctypes.synchronized
# polyglot-covers: python.multiprocessing.shared-memory-pointer-trap

import ctypes
import multiprocessing
import multiprocessing.sharedctypes


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _increment_with_wrapper_lock(counter, repetitions):
    for _ in range(repetitions):
        with counter.get_lock():
            counter.value += 1


def _square_shared_objects(number, text, points):
    with number.get_lock():
        number.value **= 2
    with text.get_lock():
        text.value = text.value.upper()
    with points.get_lock():
        for point in points:
            point.x **= 2
            point.y **= 2


def test_value_wrapper_exposes_underlying_ctypes_object_and_lock():
    """lock=False 直接返回 ctypes object，不再提供 get_obj/get_lock。"""

    synchronized = multiprocessing.Value("i", 7)
    raw = multiprocessing.Value("i", 9, lock=False)

    assert synchronized.value == 7
    assert synchronized.get_obj().value == 7
    assert synchronized.get_lock() is not None
    assert isinstance(raw, ctypes.c_int)
    assert raw.value == 9
    assert not hasattr(raw, "get_lock")


def test_explicit_wrapper_lock_makes_compound_increment_atomic_across_processes():
    """三名 child 各递增 500 次；lock 覆盖完整 read-modify-write。"""

    context = multiprocessing.get_context("spawn")
    counter = context.Value("i", 0)
    processes = [
        context.Process(
            target=_increment_with_wrapper_lock,
            args=(counter, 500),
        )
        for _ in range(3)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0
        process.close()

    assert counter.value == 1500


def test_char_array_distinguishes_nul_terminated_value_and_full_raw_storage():
    """Array('c') 保留 ctypes char array 的 value/raw semantics。"""

    text = multiprocessing.Array("c", b"hello\x00world")

    assert text.value == b"hello"
    assert text.raw == b"hello\x00world"
    with text.get_lock():
        text.value = b"hi"
    assert text.value == b"hi"


def test_shared_structure_and_array_are_mutated_by_spawned_child():
    """Structure fields 是 shared bytes；案例不存 pointer，只存可跨 address space 的值。"""

    context = multiprocessing.get_context("spawn")
    number = context.Value("i", 7)
    shared_lock = context.RLock()
    text = context.Array("c", b"hello world", lock=shared_lock)
    points = context.Array(
        _Point,
        [(2.0, -3.0), (4.0, 5.0)],
        lock=shared_lock,
    )
    process = context.Process(
        target=_square_shared_objects,
        args=(number, text, points),
    )

    process.start()
    process.join(timeout=5)

    assert process.exitcode == 0
    assert number.value == 49
    assert text.value == b"HELLO WORLD"
    assert [(point.x, point.y) for point in points] == [(4.0, 9.0), (16.0, 25.0)]
    process.close()


def test_sharedctypes_raw_copy_and_synchronized_adapter():
    """copy 产生新的 shared allocation；synchronized 为既有 ctypes object 加 wrapper。"""

    raw_point = multiprocessing.sharedctypes.RawValue(_Point, 1.5, 2.5)
    raw_numbers = multiprocessing.sharedctypes.RawArray("i", [1, 2, 3])
    copied_point = multiprocessing.sharedctypes.copy(raw_point)
    lock = multiprocessing.RLock()
    wrapped = multiprocessing.sharedctypes.synchronized(raw_numbers, lock)

    assert (raw_point.x, raw_point.y) == (1.5, 2.5)
    assert (copied_point.x, copied_point.y) == (1.5, 2.5)
    copied_point.x = 99.0
    assert raw_point.x == 1.5

    assert wrapped.get_obj() is raw_numbers
    assert wrapped.get_lock() is lock
    with wrapped:
        wrapped[1] = 20
    assert list(raw_numbers) == [1, 20, 3]


def test_sharedctypes_value_and_array_select_synchronized_or_raw_result():
    """sharedctypes.Value/Array 的 lock keyword 与 top-level factory 遵循同一规则。"""

    value = multiprocessing.sharedctypes.Value("d", 1.25)
    array = multiprocessing.sharedctypes.Array("h", [2, 4, 6])
    raw_value = multiprocessing.sharedctypes.Value("i", 8, lock=False)

    assert value.value == 1.25
    assert list(array) == [2, 4, 6]
    assert isinstance(raw_value, ctypes.c_int)
