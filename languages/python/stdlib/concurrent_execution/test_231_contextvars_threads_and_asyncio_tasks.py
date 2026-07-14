"""231｜Context 的 thread top-level isolation 与 ``asyncio.Task`` propagation。

每个 OS thread 有独立的 top-level Context，新 thread 不自动继承创建者 binding；需要时
显式把 ``copy_context().run`` 作为 target。asyncio 则在 Task 创建时自动复制 current
Context，使 sibling tasks 可继承共同起点又各自修改，不发生 request-local 状态串线。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.contextvars.thread-top-level-context
# polyglot-covers: python.contextvars.new-thread-does-not-inherit-context
# polyglot-covers: python.contextvars.copy-context-to-thread
# polyglot-covers: python.contextvars.asyncio-native-support
# polyglot-covers: python.contextvars.asyncio-task-context-capture
# polyglot-covers: python.contextvars.asyncio-task-creation-snapshot
# polyglot-covers: python.contextvars.asyncio-sibling-task-isolation

import asyncio
import contextvars
import queue
import threading


REQUEST_ID = contextvars.ContextVar("async_request_id")


def test_new_thread_is_empty_unless_captured_context_is_run_explicitly():
    """同一 Context object 只能单点进入，但 copy 可安全交给此时尚未进入它的 worker。"""

    results = queue.Queue()

    def scenario():
        REQUEST_ID.set("main-request")
        captured = contextvars.copy_context()

        plain = threading.Thread(
            target=lambda: results.put(("plain", REQUEST_ID.get("missing")))
        )
        propagated = threading.Thread(
            target=captured.run,
            args=(lambda: results.put(("propagated", REQUEST_ID.get())),),
        )
        plain.start()
        propagated.start()
        plain.join()
        propagated.join()

    contextvars.Context().run(scenario)

    assert sorted([results.get_nowait(), results.get_nowait()]) == [
        ("plain", "missing"),
        ("propagated", "main-request"),
    ]


def test_task_captures_context_at_creation_not_first_execution():
    """parent 在 create_task 后重新绑定；尚未放行的 child 仍看到创建瞬间的值。"""

    async def scenario():
        gate = asyncio.Event()
        REQUEST_ID.set("captured-at-create")

        async def child():
            await gate.wait()
            return REQUEST_ID.get()

        task = asyncio.create_task(child())
        REQUEST_ID.set("parent-after-create")
        gate.set()

        return await task, REQUEST_ID.get()

    result = contextvars.Context().run(lambda: asyncio.run(scenario()))

    assert result == ("captured-at-create", "parent-after-create")


def test_sibling_tasks_mutate_independent_context_copies():
    """两个 Task 都继承 parent，随后各自 set；Event 让两者都写完再读取。"""

    async def scenario():
        REQUEST_ID.set("parent")
        ready = []
        both_ready = asyncio.Event()

        async def child(value):
            assert REQUEST_ID.get() == "parent"
            REQUEST_ID.set(value)
            ready.append(value)
            if len(ready) == 2:
                both_ready.set()
            await both_ready.wait()
            return REQUEST_ID.get()

        results = await asyncio.gather(child("left"), child("right"))
        return results, REQUEST_ID.get()

    results, parent_value = contextvars.Context().run(
        lambda: asyncio.run(scenario())
    )

    assert results == ["left", "right"]
    assert parent_value == "parent"
