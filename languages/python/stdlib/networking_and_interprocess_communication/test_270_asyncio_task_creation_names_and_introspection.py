"""270｜``create_task``、Task naming、cooperative scheduling 与 introspection。

Task 把 coroutine 安排到当前 running loop，并在每个 await suspension point 与其他 Task
协作切换。event loop 只保留 Task 弱引用，可靠的 background work 应保存强引用并在完成
callback 中移除。current_task/all_tasks 只反映当前 loop 中尚未完成的 Task。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.create_task
# polyglot-covers: python.asyncio.create-task-requires-running-loop
# polyglot-covers: python.asyncio.Task
# polyglot-covers: python.asyncio.Task.get_name
# polyglot-covers: python.asyncio.Task.set_name
# polyglot-covers: python.asyncio.Task.get_coro
# polyglot-covers: python.asyncio.Task.done
# polyglot-covers: python.asyncio.Task.result
# polyglot-covers: python.asyncio.current_task
# polyglot-covers: python.asyncio.all_tasks
# polyglot-covers: python.asyncio.cooperative-task-scheduling
# polyglot-covers: python.asyncio.background-task-strong-reference
# polyglot-covers: python.asyncio.background-task-self-discard

import asyncio

import pytest


def test_create_task_outside_a_running_loop_rejects_the_coroutine():
    async def work():
        return 1

    coroutine = work()
    try:
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.create_task(coroutine)
    finally:
        coroutine.close()


def test_task_name_coroutine_and_introspection_follow_lifecycle():
    async def scenario():
        gate = asyncio.Event()

        async def worker():
            await gate.wait()
            return 42

        coroutine = worker()
        task = asyncio.create_task(coroutine, name="initial-name")
        assert task.get_name() == "initial-name"
        assert task.get_coro() is coroutine
        assert task.done() is False
        assert task in asyncio.all_tasks()
        assert asyncio.current_task() is not task

        assert task.set_name(2026) is None
        assert task.get_name() == "2026"
        assert "2026" in repr(task)

        gate.set()
        assert await task == 42
        assert task.done() is True
        assert task.result() == 42
        assert task not in asyncio.all_tasks()

    asyncio.run(scenario())

def test_events_make_cooperative_interleaving_explicit_without_wall_clock_delays():
    async def scenario():
        both_started = asyncio.Event()
        release = asyncio.Event()
        trace = []

        async def worker(label):
            trace.append((label, "started"))
            if len(trace) == 2:
                both_started.set()
            await release.wait()
            trace.append((label, "finished"))
            return label

        left = asyncio.create_task(worker("left"))
        right = asyncio.create_task(worker("right"))
        await both_started.wait()
        assert trace == [("left", "started"), ("right", "started")]

        release.set()
        assert await asyncio.gather(left, right) == ["left", "right"]
        assert trace[-2:] == [("left", "finished"), ("right", "finished")]

    asyncio.run(scenario())


def test_background_task_set_keeps_strong_reference_then_discards_completion():
    async def scenario():
        background = set()
        gate = asyncio.Event()

        async def worker():
            await gate.wait()
            return "done"

        task = asyncio.create_task(worker())
        background.add(task)
        task.add_done_callback(background.discard)
        assert background == {task}

        gate.set()
        assert await task == "done"
        # done callback 由 loop 安排在下一轮；用 Future callback 明确推进一轮。
        callback_turn = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(callback_turn.set_result, None)
        await callback_turn
        assert background == set()

    asyncio.run(scenario())
