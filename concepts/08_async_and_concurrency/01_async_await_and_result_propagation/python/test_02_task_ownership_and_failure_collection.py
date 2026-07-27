"""任务所有权、结果复用与失败收集。

共同问题：异步结果能否被多个观察者复用；组合失败是否取消其他工作；
调用方如何选择快速失败或把失败作为结果收集。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/python/stdlib/095-103_networking_and_interprocess_communication/
# polyglot-related+: test_095_asyncio_coroutines_tasks_futures_threads_and_errors.py

import asyncio


def test_task_result_can_be_awaited_repeatedly_after_completion():
    async def scenario():
        calls = 0

        async def work():
            nonlocal calls
            calls += 1
            return 42

        task = asyncio.create_task(work())
        first = await task
        second = await task
        return first, second, calls

    assert asyncio.run(scenario()) == (42, 42, 1)

    # coroutine object 本身完成后不可复用；Task/Future 持有完成状态，可供多个观察者读取。


def test_gather_can_collect_failures_in_input_order():
    async def scenario():
        async def fail():
            raise ValueError("failed")

        return await asyncio.gather(
            asyncio.sleep(0, result=1),
            fail(),
            return_exceptions=True,
        )

    results = asyncio.run(scenario())

    assert results[0] == 1
    assert isinstance(results[1], ValueError)
    assert str(results[1]) == "failed"

    # return_exceptions=False 会向等待者传播首个失败，但不等于结构化取消所有其他任务；
    # 所有权与取消策略必须由调用方显式安排。
