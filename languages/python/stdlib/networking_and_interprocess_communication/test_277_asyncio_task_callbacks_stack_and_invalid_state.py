"""277｜Task callback API、suspended stack、Future-like state 与只读结果。

Task 继承大部分 Future protocol，但其结果由 coroutine 决定，不能调用 set_result 或
set_exception。pending Task 的 result/exception 是 InvalidStateError。get_stack/print_stack
用于诊断 suspension point；成功或取消后 stack 为空。done callback 由 loop 调度执行。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Task.add_done_callback
# polyglot-covers: python.asyncio.Task.remove_done_callback
# polyglot-covers: python.asyncio.Task-callback-loop-scheduling
# polyglot-covers: python.asyncio.Task.get_stack
# polyglot-covers: python.asyncio.Task.print_stack
# polyglot-covers: python.asyncio.Task-success-stack-empty
# polyglot-covers: python.asyncio.Task.result-pending-invalid-state
# polyglot-covers: python.asyncio.Task.exception-pending-invalid-state
# polyglot-covers: python.asyncio.Task-set-result-forbidden
# polyglot-covers: python.asyncio.Task-set-exception-forbidden
# polyglot-covers: python.asyncio.InvalidStateError

import asyncio
import io

import pytest


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_done_callbacks_can_be_removed_and_run_via_event_loop():
    async def scenario():
        release = asyncio.Event()
        calls = []

        async def worker():
            await release.wait()
            return 42

        task = asyncio.create_task(worker())

        def removed(completed):
            calls.append(("removed", completed.result()))

        def kept(completed):
            calls.append(("kept", completed.result()))

        task.add_done_callback(removed)
        task.add_done_callback(removed)
        task.add_done_callback(kept)
        assert task.remove_done_callback(removed) == 2

        release.set()
        assert await task == 42
        await _next_loop_turn()
        assert calls == [("kept", 42)]

    asyncio.run(scenario())

def test_suspended_task_exposes_one_stack_frame_and_printable_diagnostic():
    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def worker():
            entered.set()
            await release.wait()
            return "done"

        task = asyncio.create_task(worker(), name="stack-example")
        await entered.wait()
        frames = task.get_stack()
        assert len(frames) == 1
        assert frames[0].f_code.co_name == "worker"

        output = io.StringIO()
        task.print_stack(file=output)
        assert "worker" in output.getvalue()

        release.set()
        assert await task == "done"
        assert task.get_stack() == []

    asyncio.run(scenario())


def test_pending_task_result_is_invalid_and_manual_completion_is_forbidden():
    async def scenario():
        task = asyncio.create_task(asyncio.Event().wait())
        with pytest.raises(asyncio.InvalidStateError):
            task.result()
        with pytest.raises(asyncio.InvalidStateError):
            task.exception()
        with pytest.raises(RuntimeError, match="Task does not support set_result"):
            task.set_result("forbidden")
        with pytest.raises(RuntimeError, match="Task does not support set_exception"):
            task.set_exception(LookupError())

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())
