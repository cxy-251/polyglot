"""任务调度、微任务与 Future。

共同问题：同步代码与调度任务的先后关系；任务何时开始；完成回调何时运行；
调度器是否由语言统一规定。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/python/language/test_015_async_functions_and_protocols.py

import asyncio


def test_call_soon_runs_after_current_callback_yields():
    async def scenario():
        events = []
        asyncio.get_running_loop().call_soon(events.append, "soon")
        events.append("sync")
        await asyncio.sleep(0)
        return events

    assert asyncio.run(scenario()) == ["sync", "soon"]


def test_create_task_schedules_coroutine_on_the_running_loop():
    async def scenario():
        events = []

        async def work():
            events.append("task")

        task = asyncio.create_task(work())
        events.append("caller")
        await task
        return events

    assert asyncio.run(scenario()) == ["caller", "task"]


def test_future_callback_runs_via_event_loop_scheduling():
    async def scenario():
        events = []
        future = asyncio.get_running_loop().create_future()
        future.add_done_callback(lambda _: events.append("callback"))
        future.set_result(42)
        events.append("set")
        await asyncio.sleep(0)
        return future.result(), events

    assert asyncio.run(scenario()) == (42, ["set", "callback"])


def test_asyncio_has_no_javascript_microtask_api():
    assert not hasattr(asyncio, "queue_microtask")

    # asyncio 由事件循环调度 callback/task；不要把其 ready queue 机械等同 ECMAScript Promise jobs。
