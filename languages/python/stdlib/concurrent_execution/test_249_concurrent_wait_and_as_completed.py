"""249｜``wait`` completion policies、duplicate elimination 与 ``as_completed`` timeout。

wait 接受来自不同 Executor 的 Futures，去重后返回 ``done/not_done`` sets。
FIRST_EXCEPTION 只在 exception terminal state 出现时提前返回；as_completed 按完成顺序
yield，每个重复 Future 只 yield 一次。timeout 从创建 iterator 的原始调用时刻计算。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.wait
# polyglot-covers: python.concurrent.futures.wait-duplicate-elimination
# polyglot-covers: python.concurrent.futures.DoneAndNotDoneFutures
# polyglot-covers: python.concurrent.futures.FIRST_COMPLETED
# polyglot-covers: python.concurrent.futures.FIRST_EXCEPTION
# polyglot-covers: python.concurrent.futures.ALL_COMPLETED
# polyglot-covers: python.concurrent.futures.as_completed
# polyglot-covers: python.concurrent.futures.as-completed-duplicate-elimination
# polyglot-covers: python.concurrent.futures.as-completed-already-done-first
# polyglot-covers: python.concurrent.futures.as-completed-timeout
# polyglot-covers: python.concurrent.futures.TimeoutError

import concurrent.futures

import pytest


def test_wait_deduplicates_and_partitions_done_from_pending():
    """timeout=0 是状态快照；named tuple fields 同时支持属性和 tuple unpack。"""

    finished = concurrent.futures.Future()
    pending = concurrent.futures.Future()
    finished.set_result("done")

    result = concurrent.futures.wait(
        [finished, finished, pending],
        timeout=0,
        return_when=concurrent.futures.ALL_COMPLETED,
    )
    done, not_done = result

    assert result.done == done == {finished}
    assert result.not_done == not_done == {pending}


def test_first_completed_and_first_exception_policies_use_terminal_states():
    """调用前完成的普通 future 计入 done；exception future 触发 FIRST_EXCEPTION。"""

    successful = concurrent.futures.Future()
    failed = concurrent.futures.Future()
    pending = concurrent.futures.Future()
    successful.set_result(1)

    completed = concurrent.futures.wait(
        [successful, pending],
        timeout=0,
        return_when=concurrent.futures.FIRST_COMPLETED,
    )
    assert completed.done == {successful}
    assert completed.not_done == {pending}

    failed.set_exception(ValueError("failed"))
    exceptional = concurrent.futures.wait(
        [successful, failed, pending],
        timeout=0,
        return_when=concurrent.futures.FIRST_EXCEPTION,
    )
    assert exceptional.done == {successful, failed}
    assert exceptional.not_done == {pending}


def test_as_completed_yields_done_once_then_times_out_for_pending():
    """finished 在 iterator 创建前已完成，因此第一个 next 立即得到它。"""

    finished = concurrent.futures.Future()
    pending = concurrent.futures.Future()
    finished.set_result(42)

    completed = concurrent.futures.as_completed(
        [finished, finished, pending],
        timeout=0,
    )

    assert next(completed) is finished
    with pytest.raises(concurrent.futures.TimeoutError):
        next(completed)


def test_as_completed_yields_each_future_once_when_all_are_done():
    first = concurrent.futures.Future()
    second = concurrent.futures.Future()
    first.set_result("first")
    second.set_result("second")

    yielded = list(concurrent.futures.as_completed([first, second, first]))

    assert set(yielded) == {first, second}
    assert len(yielded) == 2
