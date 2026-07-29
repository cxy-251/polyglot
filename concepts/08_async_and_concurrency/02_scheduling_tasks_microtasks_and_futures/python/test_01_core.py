"""任务调度、微任务与 Future。

共同问题：同步代码与调度任务的先后关系；任务何时开始；完成回调何时运行；
调度器是否由语言统一规定。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/python/stdlib/095-103_networking_and_interprocess_communication/
# polyglot-related+: test_095_asyncio_coroutines_tasks_futures_threads_and_errors.py

import asyncio


def test_ready_callbacks_and_tasks_run_only_after_the_current_code_yields():
    async def scenario():
        events = []
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        future.add_done_callback(lambda _: events.append("future callback"))

        async def work():
            events.append("task")

        loop.call_soon(events.append, "call_soon")
        task = asyncio.create_task(work())
        future.set_result(42)
        events.append("sync")
        assert events == ["sync"]

        await asyncio.sleep(0)
        events.append("resumed")
        await task
        return events

    assert asyncio.run(scenario()) == [
        "sync",
        "call_soon",
        "task",
        "future callback",
        "resumed",
    ]

    # asyncio 的 ready queue 与 ECMAScript Promise job queue 是不同调度模型；这里只
    # 断言 Python 3.10 asyncio 在明确让出边界前不执行已排队 callback/task。


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
