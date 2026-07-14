"""293｜loop task factory、``run_in_executor`` 与 default executor shutdown。

task factory 让替代 event loop/instrumentation 控制 Task 构造；恢复 None 即默认工厂。
run_in_executor 返回 asyncio Future，positional args 原样传入，keyword 应使用 partial。
shutdown_default_executor 会 join worker，之后该 loop 不允许再次使用默认 executor。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.create_task
# polyglot-covers: python.asyncio.loop.set_task_factory
# polyglot-covers: python.asyncio.loop.get_task_factory
# polyglot-covers: python.asyncio.task-factory-loop-coro-signature
# polyglot-covers: python.asyncio.task-factory-reset-none
# polyglot-covers: python.asyncio.loop.run_in_executor
# polyglot-covers: python.asyncio.run-in-executor-asyncio-future
# polyglot-covers: python.asyncio.run-in-executor-args
# polyglot-covers: python.asyncio.run-in-executor-keywords-partial
# polyglot-covers: python.asyncio.loop.set_default_executor
# polyglot-covers: python.asyncio.default-executor-thread-pool-only
# polyglot-covers: python.asyncio.loop.shutdown_default_executor
# polyglot-covers: python.asyncio.default-executor-use-after-shutdown

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import threading

import pytest


def test_custom_task_factory_receives_loop_and_coroutine_then_can_be_reset():
    async def scenario():
        loop = asyncio.get_running_loop()
        created = []

        def factory(received_loop, coroutine):
            created.append((received_loop, coroutine))
            return asyncio.Task(coroutine, loop=received_loop)

        loop.set_task_factory(factory)
        assert loop.get_task_factory() is factory

        async def compute():
            return 42

        task = loop.create_task(compute(), name="factory-task")
        assert await task == 42
        assert created == [(loop, task.get_coro())]
        assert task.get_name() == "factory-task"

        loop.set_task_factory(None)
        assert loop.get_task_factory() is None

    asyncio.run(scenario())


def test_run_in_executor_uses_thread_pool_and_partial_for_keywords():
    def compute(value, *, multiplier):
        return value * multiplier, threading.get_ident()

    async def scenario():
        loop = asyncio.get_running_loop()
        caller_ident = threading.get_ident()
        future = loop.run_in_executor(None, partial(compute, 6, multiplier=7))
        assert asyncio.isfuture(future) is True
        result, worker_ident = await future
        return result, worker_ident, caller_ident

    result, worker_ident, caller_ident = asyncio.run(scenario())
    assert result == 42
    assert worker_ident != caller_ident


def test_default_executor_must_be_thread_pool_and_shutdown_is_terminal_for_loop():
    loop = asyncio.new_event_loop()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="polyglot-default")
    try:
        with pytest.raises(TypeError, match="executor must be ThreadPoolExecutor instance"):
            loop.set_default_executor(object())

        loop.set_default_executor(executor)

        async def use_then_shutdown():
            name = await loop.run_in_executor(None, threading.current_thread)
            assert name.name.startswith("polyglot-default")
            await loop.shutdown_default_executor()
            with pytest.raises(RuntimeError, match="Executor shutdown has been called"):
                loop.run_in_executor(None, lambda: None)

        loop.run_until_complete(use_then_shutdown())
    finally:
        loop.close()
        executor.shutdown()
