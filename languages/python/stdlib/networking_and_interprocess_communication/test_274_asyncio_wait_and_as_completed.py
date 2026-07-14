"""274｜``wait`` completion policies 与 ``as_completed`` completion-order iterator。

wait 返回 done/pending sets；timeout 只结束等待，不取消 pending。Python 3.10 仍会接收
coroutine object 但已弃用，而且返回隐式创建的 Task，造成 identity confusion；应先显式
create_task。as_completed 则返回 coroutine iterator，每次 await 取得下一项完成结果。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.wait
# polyglot-covers: python.asyncio.wait-empty-error
# polyglot-covers: python.asyncio.wait-timeout-no-cancel
# polyglot-covers: python.asyncio.FIRST_COMPLETED
# polyglot-covers: python.asyncio.FIRST_EXCEPTION
# polyglot-covers: python.asyncio.ALL_COMPLETED
# polyglot-covers: python.asyncio.wait-coroutine-deprecated-in-3.10
# polyglot-covers: python.asyncio.wait-implicit-task-identity-trap
# polyglot-covers: python.asyncio.as_completed
# polyglot-covers: python.asyncio.as-completed-coroutine-iterator
# polyglot-covers: python.asyncio.as-completed-timeout
# polyglot-covers: python.asyncio.as-completed-timeout-no-cancel

import asyncio

import pytest


def test_wait_rejects_empty_input_and_timeout_does_not_cancel_pending_task():
    async def scenario():
        with pytest.raises(ValueError, match="Set of Tasks/Futures is empty"):
            await asyncio.wait([])

        started = asyncio.Event()
        release = asyncio.Event()

        async def worker():
            started.set()
            await release.wait()
            return "done"

        task = asyncio.create_task(worker())
        await started.wait()
        done, pending = await asyncio.wait(
            {task},
            timeout=0,
            return_when=asyncio.ALL_COMPLETED,
        )

        assert done == set()
        assert pending == {task}
        assert task.cancelled() is False
        release.set()
        assert await task == "done"

    asyncio.run(scenario())

def test_wait_first_completed_and_first_exception_partition_existing_states():
    async def scenario():
        loop = asyncio.get_running_loop()
        successful = loop.create_future()
        failed = loop.create_future()
        pending = loop.create_future()
        successful.set_result(1)

        done, not_done = await asyncio.wait(
            {successful, pending},
            return_when=asyncio.FIRST_COMPLETED,
        )
        assert done == {successful}
        assert not_done == {pending}

        failed.set_exception(LookupError("missing"))
        done, not_done = await asyncio.wait(
            {successful, failed, pending},
            return_when=asyncio.FIRST_EXCEPTION,
        )
        assert done == {successful, failed}
        assert not_done == {pending}
        assert isinstance(failed.exception(), LookupError)
        pending.cancel()

    asyncio.run(scenario())


def test_python_310_wait_wraps_direct_coroutine_and_returns_a_different_task():
    async def scenario():
        async def compute():
            return 42

        coroutine = compute()
        with pytest.warns(DeprecationWarning, match="coroutine objects to asyncio.wait"):
            done, pending = await asyncio.wait({coroutine})

        assert pending == set()
        assert coroutine not in done
        assert len(done) == 1
        implicit_task = done.pop()
        assert isinstance(implicit_task, asyncio.Task)
        assert implicit_task.result() == 42

    asyncio.run(scenario())


def test_as_completed_yields_result_coroutines_and_times_out_without_cancelling():
    async def scenario():
        loop = asyncio.get_running_loop()
        first = loop.create_future()
        second = loop.create_future()
        first.set_result("first")
        second.set_result("second")

        completions = asyncio.as_completed([first, second])
        results = [await completion for completion in completions]
        assert sorted(results) == ["first", "second"]

        pending = asyncio.create_task(asyncio.Event().wait())
        timed = asyncio.as_completed([pending], timeout=0)
        with pytest.raises(asyncio.TimeoutError):
            await next(timed)
        assert pending.cancelled() is False
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)

    asyncio.run(scenario())
