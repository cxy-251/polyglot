"""272｜``asyncio.gather`` 的有序聚合、异常和取消传播。

gather 并发调度 awaitables，却始终按输入顺序返回结果。默认第一个异常会立刻传播，但不会
自动取消其他 child；return_exceptions=True 才把异常当结果。取消 gather 会取消未完成的
child，而 gather 已因异常 done 后再 cancel 不会追溯取消仍在运行的 sibling。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.gather
# polyglot-covers: python.asyncio.gather-auto-task-scheduling
# polyglot-covers: python.asyncio.gather-input-order
# polyglot-covers: python.asyncio.gather-first-exception
# polyglot-covers: python.asyncio.gather-siblings-not-cancelled-on-error
# polyglot-covers: python.asyncio.gather-return_exceptions
# polyglot-covers: python.asyncio.gather-child-cancelled-as-result
# polyglot-covers: python.asyncio.gather-cancellation-propagation
# polyglot-covers: python.asyncio.gather-cancel-after-done-noop

import asyncio

import pytest


def test_gather_results_follow_input_order_not_completion_order():
    async def scenario():
        left_gate = asyncio.Event()
        right_gate = asyncio.Event()
        completed = []

        async def worker(label, gate):
            await gate.wait()
            completed.append(label)
            return label

        group = asyncio.gather(
            worker("left", left_gate),
            worker("right", right_gate),
        )
        right_gate.set()
        turn = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(turn.set_result, None)
        await turn
        assert completed == ["right"]

        left_gate.set()
        assert await group == ["left", "right"]
        assert completed == ["right", "left"]

    asyncio.run(scenario())

def test_default_error_propagation_leaves_sibling_running_and_late_cancel_is_noop():
    async def scenario():
        survivor_started = asyncio.Event()
        survivor_gate = asyncio.Event()

        async def fail():
            raise LookupError("first failure")

        async def survive():
            survivor_started.set()
            await survivor_gate.wait()
            return "survived"

        survivor = asyncio.create_task(survive())
        group = asyncio.gather(fail(), survivor)
        await survivor_started.wait()
        with pytest.raises(LookupError, match="first failure"):
            await group

        assert group.done() is True
        assert group.cancel() is False
        assert survivor.cancelled() is False
        survivor_gate.set()
        assert await survivor == "survived"

    asyncio.run(scenario())


def test_return_exceptions_collects_failures_and_cancelled_children():
    async def scenario():
        async def fail():
            raise ValueError("bad value")

        cancelled = asyncio.create_task(asyncio.Event().wait())
        cancelled.cancel()
        results = await asyncio.gather(
            asyncio.sleep(0, result="ok"),
            fail(),
            cancelled,
            return_exceptions=True,
        )

        assert results[0] == "ok"
        assert isinstance(results[1], ValueError)
        assert isinstance(results[2], asyncio.CancelledError)

    asyncio.run(scenario())


def test_cancelling_gather_cancels_each_pending_child():
    async def scenario():
        entered = [asyncio.Event(), asyncio.Event()]
        blocker = asyncio.Event()

        async def worker(index):
            entered[index].set()
            await blocker.wait()

        children = [asyncio.create_task(worker(index)) for index in range(2)]
        group = asyncio.gather(*children)
        await asyncio.gather(*(event.wait() for event in entered))

        assert group.cancel() is True
        with pytest.raises(asyncio.CancelledError):
            await group
        assert all(child.cancelled() for child in children)

    asyncio.run(scenario())
