"""288｜asyncio Queue ``task_done/join`` 与 cancellable worker workflow。

get 让 Queue 变空并不等于 work 已处理；每个 put 增加 unfinished count，每个 consumer 必须
恰好一次 task_done。join 只等计数归零。长驻 worker 常在 queue.join 后 cancel，并用 gather
回收取消异常；task_done 应置于 finally，防止业务异常把 join 永久卡住。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Queue.task_done
# polyglot-covers: python.asyncio.Queue.join
# polyglot-covers: python.asyncio.Queue-unfinished-task-counter
# polyglot-covers: python.asyncio.Queue-get-does-not-finish-task
# polyglot-covers: python.asyncio.Queue-join-processing-not-emptiness
# polyglot-covers: python.asyncio.Queue-task-done-exactly-once
# polyglot-covers: python.asyncio.Queue-task-done-overcall
# polyglot-covers: python.asyncio.Queue-worker-task-done-finally
# polyglot-covers: python.asyncio.Queue-cancel-workers-after-join

import asyncio

import pytest


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_workers_acknowledge_each_item_then_are_cancelled_after_join():
    async def scenario():
        work = asyncio.Queue()
        processed = []

        async def worker():
            while True:
                item = await work.get()
                try:
                    processed.append(item * item)
                finally:
                    work.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(2)]
        for item in (2, 3, 4):
            work.put_nowait(item)

        await work.join()
        for task in workers:
            task.cancel()
        results = await asyncio.gather(*workers, return_exceptions=True)

        assert sorted(processed) == [4, 9, 16]
        assert all(isinstance(result, asyncio.CancelledError) for result in results)

    asyncio.run(scenario())

def test_join_waits_for_task_done_even_after_item_has_been_removed():
    async def scenario():
        work = asyncio.Queue()
        work.put_nowait("retrieved")
        assert work.get_nowait() == "retrieved"
        assert work.empty() is True

        joined = asyncio.create_task(work.join())
        await _next_loop_turn()
        assert joined.done() is False

        work.task_done()
        await joined
        with pytest.raises(ValueError, match="task_done\(\) called too many times"):
            work.task_done()

    asyncio.run(scenario())
