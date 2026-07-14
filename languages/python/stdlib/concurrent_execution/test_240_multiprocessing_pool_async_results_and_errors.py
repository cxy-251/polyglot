"""240｜Pool async results、timeout、callbacks 与 remote exception transport。

``apply_async/map_async`` 立即返回 AsyncResult；``get`` 才重抛 worker 异常。callback 在
parent 的 result-handler thread 运行，必须快速且不能抛出。用 initializer 注入 Event，
可确定制造 pending result 并测试 TimeoutError，不用 sleep 猜 worker 调度。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Pool.apply_async
# polyglot-covers: python.multiprocessing.Pool.map_async
# polyglot-covers: python.multiprocessing.pool.AsyncResult
# polyglot-covers: python.multiprocessing.AsyncResult.ready
# polyglot-covers: python.multiprocessing.AsyncResult.wait
# polyglot-covers: python.multiprocessing.AsyncResult.get
# polyglot-covers: python.multiprocessing.AsyncResult.successful
# polyglot-covers: python.multiprocessing.TimeoutError
# polyglot-covers: python.multiprocessing.pool-callback
# polyglot-covers: python.multiprocessing.pool-error-callback
# polyglot-covers: python.multiprocessing.pool-remote-exception
# polyglot-covers: python.multiprocessing.pool.RemoteTraceback
# polyglot-covers: python.multiprocessing.Pool.terminate

import multiprocessing

import pytest


_POOL_GATE = None


def _install_pool_gate(gate):
    global _POOL_GATE
    _POOL_GATE = gate


def _wait_for_pool_gate(value):
    if not _POOL_GATE.wait(timeout=5):
        raise RuntimeError("pool gate timed out")
    return value


def _triple(value):
    return value * 3


def _fail_pool_task(message):
    raise ValueError(message)


def test_async_result_pending_success_and_timeout_protocol():
    """successful 只在 ready 后合法；wait 返回 None，get 返回 task value。"""

    context = multiprocessing.get_context("spawn")
    gate = context.Event()
    pool = context.Pool(
        processes=1,
        initializer=_install_pool_gate,
        initargs=(gate,),
    )
    result = pool.apply_async(_wait_for_pool_gate, args=(42,))

    try:
        assert result.ready() is False
        assert result.wait(timeout=0) is None
        with pytest.raises(ValueError, match="not ready"):
            result.successful()
        with pytest.raises(multiprocessing.TimeoutError):
            result.get(timeout=0)

        gate.set()
        assert result.get(timeout=5) == 42
        assert result.ready() is True
        assert result.successful() is True
    finally:
        gate.set()
        pool.close()
        pool.join()


def test_async_callbacks_run_for_success_and_error_paths():
    """get 建立 callback 已执行的完成边界；error_callback 收到 reconstructed exception。"""

    context = multiprocessing.get_context("spawn")
    successes = []
    failures = []

    with context.Pool(processes=1) as pool:
        successful = pool.apply_async(
            _triple,
            args=(7,),
            callback=successes.append,
            error_callback=failures.append,
        )
        failed = pool.apply_async(
            _fail_pool_task,
            args=("remote failure",),
            callback=successes.append,
            error_callback=failures.append,
        )

        assert successful.get(timeout=5) == 21
        with pytest.raises(ValueError, match="remote failure") as raised:
            failed.get(timeout=5)

    assert successes == [21]
    assert len(failures) == 1
    assert isinstance(failures[0], ValueError)
    assert str(failures[0]) == "remote failure"
    assert raised.value.__cause__.__class__.__name__ == "RemoteTraceback"


def test_map_async_returns_ordered_list_and_pool_terminate_is_explicit():
    """terminate 停止 worker 且丢弃未完成 task；正常结果先 get，再显式终止空闲 pool。"""

    context = multiprocessing.get_context("spawn")
    pool = context.Pool(processes=2)

    try:
        result = pool.map_async(_triple, [1, 2, 3], chunksize=1)
        assert result.get(timeout=5) == [3, 6, 9]
    finally:
        pool.terminate()
        pool.join()
