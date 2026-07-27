"""ready queue、完成回调与显式执行边界。

共同问题：已经完成的结果何时通知后来观察者；同一队列是否保持登记顺序；
创建结果对象是否等同于启动工作。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/python/stdlib/095-103_networking_and_interprocess_communication/
# polyglot-related+: test_095_asyncio_coroutines_tasks_futures_threads_and_errors.py

import asyncio


def test_done_callback_added_after_completion_is_still_scheduled():
    async def scenario():
        events = []
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        future.set_result(42)

        loop.call_soon(events.append, "first")
        future.add_done_callback(lambda _: events.append("future"))
        loop.call_soon(events.append, "last")
        events.append("sync")

        await asyncio.sleep(0)
        events.append("resumed")
        return events

    assert asyncio.run(scenario()) == [
        "sync",
        "first",
        "future",
        "last",
        "resumed",
    ]

    # set_result 不同步调用 callback；即使 callback 后登记，也进入 asyncio ready queue。


def test_creating_a_future_does_not_schedule_work():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        await asyncio.sleep(0)
        assert not future.done()
        future.set_result(42)
        return await future

    assert asyncio.run(scenario()) == 42
