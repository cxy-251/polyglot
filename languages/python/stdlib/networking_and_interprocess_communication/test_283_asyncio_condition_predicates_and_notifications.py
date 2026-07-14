"""283｜asyncio Condition 的共享 Lock、predicate loop 与 notification ownership。

Condition 把 Event-style 通知与 Lock-style exclusive state access 合并。wait 会原子释放底层
lock，唤醒后再 acquire 才返回；因此状态检查必须在 lock 内用 wait_for predicate 循环。
notify/notify_all 只唤醒 waiter，不释放 lock，而且未持锁调用会抛 RuntimeError。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Condition
# polyglot-covers: python.asyncio.Condition-shared-lock
# polyglot-covers: python.asyncio.Condition.acquire
# polyglot-covers: python.asyncio.Condition.release
# polyglot-covers: python.asyncio.Condition.locked
# polyglot-covers: python.asyncio.Condition.wait
# polyglot-covers: python.asyncio.Condition.wait_for
# polyglot-covers: python.asyncio.Condition.notify
# polyglot-covers: python.asyncio.Condition.notify_all
# polyglot-covers: python.asyncio.Condition-wait-releases-reacquires
# polyglot-covers: python.asyncio.Condition-predicate-final-value
# polyglot-covers: python.asyncio.Condition-notify-does-not-release
# polyglot-covers: python.asyncio.Condition-lock-required

import asyncio

import pytest


def test_wait_for_releases_then_reacquires_shared_lock_and_returns_predicate_value():
    async def scenario():
        lock = asyncio.Lock()
        condition = asyncio.Condition(lock)
        sibling_condition = asyncio.Condition(lock)
        waiter_ready = asyncio.Event()
        state = {"value": ""}

        async def waiter():
            async with condition:
                waiter_ready.set()
                result = await condition.wait_for(lambda: state["value"])
                assert condition.locked() is True
                assert sibling_condition.locked() is True
                return result

        task = asyncio.create_task(waiter())
        await waiter_ready.wait()
        # waiter 只有进入 condition.wait 并释放 lock 后，producer 才能获得同一把 lock。
        async with condition:
            state["value"] = "ready"
            condition.notify(1)
            assert task.done() is False

        assert await task == "ready"

    asyncio.run(scenario())

def test_notify_all_wakes_every_waiter_after_notifier_releases_lock():
    async def scenario():
        condition = asyncio.Condition()
        all_waiting = asyncio.Event()
        ready_count = 0
        resumed = []

        async def waiter(label):
            nonlocal ready_count
            async with condition:
                ready_count += 1
                if ready_count == 2:
                    all_waiting.set()
                assert await condition.wait() is True
                resumed.append(label)

        tasks = [asyncio.create_task(waiter(label)) for label in ("a", "b")]
        await all_waiting.wait()
        async with condition:
            condition.notify_all()
            assert resumed == []

        await asyncio.gather(*tasks)
        assert sorted(resumed) == ["a", "b"]

    asyncio.run(scenario())


def test_wait_and_notify_require_condition_lock_ownership():
    async def scenario():
        condition = asyncio.Condition()

        with pytest.raises(RuntimeError, match="cannot notify on un-acquired lock"):
            condition.notify()
        with pytest.raises(RuntimeError, match="cannot wait on un-acquired lock"):
            await condition.wait()
        with pytest.raises(RuntimeError, match="Lock is not acquired"):
            condition.release()

    asyncio.run(scenario())
