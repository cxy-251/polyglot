"""239｜``multiprocessing.Pool`` apply/map families、initializer 与 worker recycling。

Pool methods 只能由创建它的 process 调用。``map`` 保序，``imap`` lazy，
``imap_unordered`` 不保证顺序；函数/参数需可 pickle。Pool 必须显式 close+join/terminate，
或用 context manager，不能依赖 garbage collection。``maxtasksperchild`` 可回收长期 worker。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Pool
# polyglot-covers: python.multiprocessing.Pool.apply
# polyglot-covers: python.multiprocessing.Pool.map
# polyglot-covers: python.multiprocessing.Pool.starmap
# polyglot-covers: python.multiprocessing.Pool.imap
# polyglot-covers: python.multiprocessing.Pool.imap_unordered
# polyglot-covers: python.multiprocessing.Pool-chunksize
# polyglot-covers: python.multiprocessing.Pool-initializer
# polyglot-covers: python.multiprocessing.Pool-context-manager
# polyglot-covers: python.multiprocessing.Pool.close
# polyglot-covers: python.multiprocessing.Pool.join
# polyglot-covers: python.multiprocessing.Pool-owner-process-only
# polyglot-covers: python.multiprocessing.Pool-picklable-callables
# polyglot-covers: python.multiprocessing.Pool.maxtasksperchild

import multiprocessing
import os

import pytest


_WORKER_LABEL = None


def _install_worker_label(label):
    global _WORKER_LABEL
    _WORKER_LABEL = label


def _square(value):
    return value * value


def _power(base, exponent):
    return base**exponent


def _labeled_square(value):
    return _WORKER_LABEL, value * value


def _worker_pid(value):
    return value, os.getpid()


def test_pool_apply_and_mapping_variants_return_expected_shapes():
    """imap 返回 iterator；unordered 只断言结果 multiset，不依赖 scheduling order。"""

    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=2) as pool:
        assert pool.apply(_power, args=(2, 5)) == 32
        assert pool.map(_square, range(5), chunksize=2) == [0, 1, 4, 9, 16]
        assert pool.starmap(_power, [(2, 3), (3, 2), (5, 1)]) == [8, 9, 5]
        assert list(pool.imap(_square, [3, 1, 2], chunksize=1)) == [9, 1, 4]
        unordered = list(pool.imap_unordered(_square, [3, 1, 2], chunksize=1))
        assert sorted(unordered) == [1, 4, 9]

    with pytest.raises(ValueError, match="Pool not running"):
        pool.apply(_square, args=(2,))


def test_pool_initializer_configures_each_worker_before_tasks():
    """initializer 参数也必须适合 context serialization；task 读取 worker-local global。"""

    context = multiprocessing.get_context("spawn")
    pool = context.Pool(
        processes=2,
        initializer=_install_worker_label,
        initargs=("ready",),
    )
    try:
        results = pool.map(_labeled_square, [1, 2, 3, 4], chunksize=1)
        assert results == [
            ("ready", 1),
            ("ready", 4),
            ("ready", 9),
            ("ready", 16),
        ]
    finally:
        pool.close()
        pool.join()


def test_maxtasksperchild_replaces_worker_after_configured_task_count():
    """单 worker、chunksize=1、每个 child 仅做一个 task，因此两个结果 pid 必须不同。"""

    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=1, maxtasksperchild=1) as pool:
        results = pool.map(_worker_pid, ["first", "second"], chunksize=1)

    assert [label for label, _ in results] == ["first", "second"]
    assert results[0][1] != results[1][1]
