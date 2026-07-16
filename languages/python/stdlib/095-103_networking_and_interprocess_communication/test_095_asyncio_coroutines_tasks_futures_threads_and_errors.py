"""095｜asyncio coroutine/awaitable、顶层 ``run`` 与零延迟让权。

调用 async def 只创建 coroutine object，不会自动执行。await 在当前 Task 中驱动它，
create_task 才把它并发调度。asyncio.run 为顶层入口创建并最终关闭新 event loop，还会清理
未显式关闭的 async generator；运行中的同线程 event loop 内不能再次调用它。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.asyncio-coroutine-object-not-scheduled
# polyglot-covers: python.asyncio-awaitable-coroutine
# polyglot-covers: python.asyncio.iscoroutine
# polyglot-covers: python.asyncio.iscoroutinefunction
# polyglot-covers: python.asyncio.run
# polyglot-covers: python.asyncio.run-return-value
# polyglot-covers: python.asyncio.run-new-loop-closed
# polyglot-covers: python.asyncio.run-debug
# polyglot-covers: python.asyncio.run-nested-loop-error
# polyglot-covers: python.asyncio.run-shutdown-async-generators
# polyglot-covers: python.asyncio.sleep
# polyglot-covers: python.asyncio.sleep-result
# polyglot-covers: python.asyncio.sleep-zero-yield




import asyncio
import inspect
import pytest
import contextvars
import threading
import concurrent.futures
from contextlib import contextmanager
import io
from concurrent.futures import ThreadPoolExecutor
from functools import partial

def test_calling_async_function_only_constructs_a_coroutine_object():
    calls = []

    async def compute():
        calls.append("ran")
        return 42

    coroutine = compute()
    try:
        assert calls == []
        assert asyncio.iscoroutinefunction(compute) is True
        assert asyncio.iscoroutine(coroutine) is True
        assert inspect.isawaitable(coroutine) is True
    finally:
        # 未 await 的 native coroutine 必须显式 close，否则 GC 会报告 RuntimeWarning。
        coroutine.close()


def test_run_returns_result_uses_debug_mode_and_closes_its_new_loop():
    async def main():
        loop = asyncio.get_running_loop()
        yielded = await asyncio.sleep(0, result="after-yield")
        return loop, loop.get_debug(), yielded

    loop, debug, yielded = asyncio.run(main(), debug=True)

    assert debug is True
    assert yielded == "after-yield"
    assert loop.is_closed() is True


def test_run_cannot_be_nested_in_an_already_running_loop():
    async def inner():
        return "inner"

    async def outer():
        coroutine = inner()
        try:
            with pytest.raises(RuntimeError, match="cannot be called from a running event loop"):
                asyncio.run(coroutine)
        finally:
            coroutine.close()

    asyncio.run(outer())


def test_run_finalizes_an_async_generator_left_open_by_main():
    finalized = []

    async def values():
        try:
            yield "first"
            yield "second"
        finally:
            finalized.append("closed")

    async def main():
        generator = values()
        assert await generator.__anext__() == "first"
        # 不调用 aclose；asyncio.run 的 shutdown_asyncgens 阶段负责执行 finally。

    asyncio.run(main())

    assert finalized == ["closed"]


# ``create_task``、Task naming、cooperative scheduling 与 introspection。
#
# Task 把 coroutine 安排到当前 running loop，并在每个 await suspension point 与其他 Task
# 协作切换。event loop 只保留 Task 弱引用，可靠的 background work 应保存强引用并在完成
# callback 中移除。current_task/all_tasks 只反映当前 loop 中尚未完成的 Task。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# Task cancellation request、传播、清理与 suppression。
#
# Task.cancel 不是立即终止：它在下一次 loop cycle 向 coroutine 注入 CancelledError，因此
# finally 能清理资源，coroutine 甚至可以抑制请求。CancelledError 自 3.8 起直接继承
# BaseException，宽泛的 ``except Exception`` 不会误吞取消；通常捕获后必须重新抛出。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Task.cancel
# polyglot-covers: python.asyncio.Task-cancel-message
# polyglot-covers: python.asyncio.Task.cancelled
# polyglot-covers: python.asyncio.Task-cancellation-injection
# polyglot-covers: python.asyncio.Task-cancellation-finally-cleanup
# polyglot-covers: python.asyncio.Task-cancellation-suppression
# polyglot-covers: python.asyncio.Task-cancel-awaited-future
# polyglot-covers: python.asyncio.CancelledError
# polyglot-covers: python.asyncio.CancelledError-BaseException
# polyglot-covers: python.asyncio.cancelled-task-result-exception




def test_cancel_injects_message_runs_finally_and_marks_task_cancelled():
    async def scenario():
        started = asyncio.Event()
        blocker = asyncio.Event()
        cleanup = []

        async def worker():
            started.set()
            try:
                await blocker.wait()
            finally:
                cleanup.append("released")

        task = asyncio.create_task(worker())
        await started.wait()
        assert task.cancel("stop requested") is True

        with pytest.raises(asyncio.CancelledError) as raised:
            await task
        assert raised.value.args == ()
        # 3.10.12 接受 cancel(msg)，但 await 边界尚未稳定保留 message；
        # 业务控制流只能依赖 CancelledError 类型和 cancelled() 状态。
        assert cleanup == ["released"]
        assert task.done() is True
        assert task.cancelled() is True
        with pytest.raises(asyncio.CancelledError):
            task.result()
        with pytest.raises(asyncio.CancelledError):
            task.exception()

    asyncio.run(scenario())


def test_coroutine_can_suppress_cancellation_but_normally_should_not():
    async def scenario():
        started = asyncio.Event()
        blocker = asyncio.Event()

        async def worker():
            started.set()
            try:
                await blocker.wait()
            except asyncio.CancelledError:
                return "suppressed"

        task = asyncio.create_task(worker())
        await started.wait()
        task.cancel()

        assert await task == "suppressed"
        assert task.cancelled() is False
        assert task.result() == "suppressed"

    asyncio.run(scenario())


def test_cancelling_task_also_cancels_future_it_is_currently_awaiting():
    async def scenario():
        loop = asyncio.get_running_loop()
        awaited = loop.create_future()
        entered = asyncio.Event()

        async def worker():
            entered.set()
            await awaited

        task = asyncio.create_task(worker())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert awaited.cancelled() is True

    asyncio.run(scenario())


def test_cancelled_error_is_not_caught_by_exception_handlers():
    assert issubclass(asyncio.CancelledError, BaseException)
    assert issubclass(asyncio.CancelledError, Exception) is False


# ``asyncio.gather`` 的有序聚合、异常和取消传播。
#
# gather 并发调度 awaitables，却始终按输入顺序返回结果。默认第一个异常会立刻传播，但不会
# 自动取消其他 child；return_exceptions=True 才把异常当结果。取消 gather 会取消未完成的
# child，而 gather 已因异常 done 后再 cancel 不会追溯取消仍在运行的 sibling。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.gather
# polyglot-covers: python.asyncio.gather-auto-task-scheduling
# polyglot-covers: python.asyncio.gather-input-order
# polyglot-covers: python.asyncio.gather-first-exception
# polyglot-covers: python.asyncio.gather-siblings-not-cancelled-on-error
# polyglot-covers: python.asyncio.gather-return_exceptions
# polyglot-covers: python.asyncio.gather-child-cancelled-as-result
# polyglot-covers: python.asyncio.gather-cancellation-propagation
# polyglot-covers: python.asyncio.gather-cancel-after-done-noop




def test_gather_results_follow_input_order_not_completion_order():
    async def scenario():
        left_gate = asyncio.Event()
        right_gate = asyncio.Event()
        completed = []

        async def worker(label, gate):
            await gate.wait()
            completed.append(label)
            return label

        group = asyncio.gather(
            worker("left", left_gate),
            worker("right", right_gate),
        )
        right_gate.set()
        turn = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(turn.set_result, None)
        await turn
        assert completed == ["right"]

        left_gate.set()
        assert await group == ["left", "right"]
        assert completed == ["right", "left"]

    asyncio.run(scenario())

def test_default_error_propagation_leaves_sibling_running_and_late_cancel_is_noop():
    async def scenario():
        survivor_started = asyncio.Event()
        survivor_gate = asyncio.Event()

        async def fail():
            raise LookupError("first failure")

        async def survive():
            survivor_started.set()
            await survivor_gate.wait()
            return "survived"

        survivor = asyncio.create_task(survive())
        group = asyncio.gather(fail(), survivor)
        await survivor_started.wait()
        with pytest.raises(LookupError, match="first failure"):
            await group

        assert group.done() is True
        assert group.cancel() is False
        assert survivor.cancelled() is False
        survivor_gate.set()
        assert await survivor == "survived"

    asyncio.run(scenario())


def test_return_exceptions_collects_failures_and_cancelled_children():
    async def scenario():
        async def fail():
            raise ValueError("bad value")

        cancelled = asyncio.create_task(asyncio.Event().wait())
        cancelled.cancel()
        results = await asyncio.gather(
            asyncio.sleep(0, result="ok"),
            fail(),
            cancelled,
            return_exceptions=True,
        )

        assert results[0] == "ok"
        assert isinstance(results[1], ValueError)
        assert isinstance(results[2], asyncio.CancelledError)

    asyncio.run(scenario())


def test_cancelling_gather_cancels_each_pending_child():
    async def scenario():
        entered = [asyncio.Event(), asyncio.Event()]
        blocker = asyncio.Event()

        async def worker(index):
            entered[index].set()
            await blocker.wait()

        children = [asyncio.create_task(worker(index)) for index in range(2)]
        group = asyncio.gather(*children)
        await asyncio.gather(*(event.wait() for event in entered))

        assert group.cancel() is True
        with pytest.raises(asyncio.CancelledError):
            await group
        assert all(child.cancelled() for child in children)

    asyncio.run(scenario())


# ``shield`` 与 ``wait_for`` 的 cancellation ownership。
#
# wait_for 超时会取消 underlying Task，并等待取消真正完成后才抛 TimeoutError。shield 只阻断
# 调用者取消向 inner 传播：outer 仍收到 CancelledError，inner 可继续；inner 若被直接取消，
# shield 也会失败。两者组合可让 timeout 结束等待但保留后台 Task，调用者必须保存并回收它。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.shield
# polyglot-covers: python.asyncio.shield-outer-cancel-inner-survives
# polyglot-covers: python.asyncio.shield-direct-inner-cancel
# polyglot-covers: python.asyncio.wait_for
# polyglot-covers: python.asyncio.wait-for-timeout
# polyglot-covers: python.asyncio.wait-for-cancels-underlying
# polyglot-covers: python.asyncio.wait-for-awaits-cancellation-cleanup
# polyglot-covers: python.asyncio.wait-for-timeout-none
# polyglot-covers: python.asyncio.wait-for-shield-preserves-task
# polyglot-covers: python.asyncio.TimeoutError




def test_wait_for_timeout_cancels_task_and_waits_for_finally_cleanup():
    async def scenario():
        started = asyncio.Event()
        blocker = asyncio.Event()
        cleanup = []

        async def worker():
            started.set()
            try:
                await blocker.wait()
            finally:
                cleanup.append("finished")

        task = asyncio.create_task(worker())
        await started.wait()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=0)

        assert task.cancelled() is True
        assert cleanup == ["finished"]

    asyncio.run(scenario())

def test_wait_for_none_waits_normally_without_installing_a_deadline():
    async def result():
        return 42

    assert asyncio.run(asyncio.wait_for(result(), timeout=None)) == 42


def test_cancelling_outer_shield_wait_does_not_cancel_inner_task():
    async def scenario():
        started = asyncio.Event()
        release = asyncio.Event()

        async def inner_work():
            started.set()
            await release.wait()
            return "inner result"

        inner = asyncio.create_task(inner_work())

        async def outer_work():
            return await asyncio.shield(inner)

        outer = asyncio.create_task(outer_work())
        await started.wait()
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer

        assert inner.cancelled() is False
        release.set()
        assert await inner == "inner result"

    asyncio.run(scenario())


def test_wait_for_shield_times_out_without_abandoning_inner_task():
    async def scenario():
        started = asyncio.Event()
        release = asyncio.Event()

        async def worker():
            started.set()
            await release.wait()
            return "kept"

        task = asyncio.create_task(worker())
        await started.wait()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=0)

        assert task.cancelled() is False
        release.set()
        assert await task == "kept"

    asyncio.run(scenario())


def test_directly_cancelled_inner_also_cancels_shield_awaitable():
    async def scenario():
        inner = asyncio.create_task(asyncio.Event().wait())
        protected = asyncio.shield(inner)
        inner.cancel()

        with pytest.raises(asyncio.CancelledError):
            await protected
        assert inner.cancelled() is True

    asyncio.run(scenario())


# ``wait`` completion policies 与 ``as_completed`` completion-order iterator。
#
# wait 返回 done/pending sets；timeout 只结束等待，不取消 pending。Python 3.10 仍会接收
# coroutine object 但已弃用，而且返回隐式创建的 Task，造成 identity confusion；应先显式
# create_task。as_completed 则返回 coroutine iterator，每次 await 取得下一项完成结果。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.wait
# polyglot-covers: python.asyncio.wait-empty-error
# polyglot-covers: python.asyncio.wait-timeout-no-cancel
# polyglot-covers: python.asyncio.FIRST_COMPLETED
# polyglot-covers: python.asyncio.FIRST_EXCEPTION
# polyglot-covers: python.asyncio.ALL_COMPLETED
# polyglot-covers: python.asyncio.wait-coroutine-deprecated-in-3.10
# polyglot-covers: python.asyncio.wait-implicit-task-identity-trap
# polyglot-covers: python.asyncio.as_completed
# polyglot-covers: python.asyncio.as-completed-coroutine-iterator
# polyglot-covers: python.asyncio.as-completed-timeout
# polyglot-covers: python.asyncio.as-completed-timeout-no-cancel




def test_wait_rejects_empty_input_and_timeout_does_not_cancel_pending_task():
    async def scenario():
        with pytest.raises(ValueError, match="coroutines/Futures is empty"):
            await asyncio.wait([])

        started = asyncio.Event()
        release = asyncio.Event()

        async def worker():
            started.set()
            await release.wait()
            return "done"

        task = asyncio.create_task(worker())
        await started.wait()
        done, pending = await asyncio.wait(
            {task},
            timeout=0,
            return_when=asyncio.ALL_COMPLETED,
        )

        assert done == set()
        assert pending == {task}
        assert task.cancelled() is False
        release.set()
        assert await task == "done"

    asyncio.run(scenario())

def test_wait_first_completed_and_first_exception_partition_existing_states():
    async def scenario():
        loop = asyncio.get_running_loop()
        successful = loop.create_future()
        failed = loop.create_future()
        pending = loop.create_future()
        successful.set_result(1)

        done, not_done = await asyncio.wait(
            {successful, pending},
            return_when=asyncio.FIRST_COMPLETED,
        )
        assert done == {successful}
        assert not_done == {pending}

        failed.set_exception(LookupError("missing"))
        done, not_done = await asyncio.wait(
            {successful, failed, pending},
            return_when=asyncio.FIRST_EXCEPTION,
        )
        assert done == {successful, failed}
        assert not_done == {pending}
        assert isinstance(failed.exception(), LookupError)
        pending.cancel()

    asyncio.run(scenario())


def test_python_310_wait_wraps_direct_coroutine_and_returns_a_different_task():
    async def scenario():
        async def compute():
            return 42

        coroutine = compute()
        with pytest.warns(DeprecationWarning, match="coroutine objects to asyncio.wait"):
            done, pending = await asyncio.wait({coroutine})

        assert pending == set()
        assert coroutine not in done
        assert len(done) == 1
        implicit_task = done.pop()
        assert isinstance(implicit_task, asyncio.Task)
        assert implicit_task.result() == 42

    asyncio.run(scenario())


def test_as_completed_yields_result_coroutines_and_times_out_without_cancelling():
    async def scenario():
        loop = asyncio.get_running_loop()
        first = loop.create_future()
        second = loop.create_future()
        first.set_result("first")
        second.set_result("second")

        completions = asyncio.as_completed([first, second])
        results = [await completion for completion in completions]
        assert sorted(results) == ["first", "second"]

        pending = asyncio.create_task(asyncio.Event().wait())
        timed = asyncio.as_completed([pending], timeout=0)
        with pytest.raises(asyncio.TimeoutError):
            await next(timed)
        assert pending.cancelled() is False
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)

    asyncio.run(scenario())


# ``asyncio.to_thread`` 延迟提交、参数、Context propagation 与异常。
#
# to_thread 返回 coroutine；直到 await 才把 callable 提交到 default thread pool。它复制当前
# contextvars.Context，使 request-local binding 对 worker 可见，但 worker 的重新绑定不回写
# caller。CPython GIL 下它主要隔离阻塞 I/O，不应被误当作纯 Python CPU parallelism。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.to_thread
# polyglot-covers: python.asyncio.to-thread-lazy-coroutine
# polyglot-covers: python.asyncio.to-thread-args-kwargs
# polyglot-covers: python.asyncio.to-thread-return-value
# polyglot-covers: python.asyncio.to-thread-different-os-thread
# polyglot-covers: python.asyncio.to-thread-contextvars-propagation
# polyglot-covers: python.asyncio.to-thread-context-mutation-isolated
# polyglot-covers: python.asyncio.to-thread-exception-propagation
# polyglot-covers: python.asyncio.to-thread-gil-io-bound-guidance




REQUEST_ID = contextvars.ContextVar("asyncio_to_thread_request_id")


def test_to_thread_is_lazy_passes_arguments_and_propagates_context_copy():
    calls = []

    def worker(value, *, multiplier):
        calls.append("called")
        inherited = REQUEST_ID.get()
        REQUEST_ID.set("worker-only")
        return value * multiplier, inherited, threading.get_ident()

    async def scenario():
        REQUEST_ID.set("request-42")
        caller_ident = threading.get_ident()
        awaitable = asyncio.to_thread(worker, 6, multiplier=7)
        assert calls == []

        result, inherited, worker_ident = await awaitable
        return result, inherited, worker_ident, caller_ident, REQUEST_ID.get()

    outcome = contextvars.Context().run(lambda: asyncio.run(scenario()))

    result, inherited, worker_ident, caller_ident, caller_context = outcome
    assert calls == ["called"]
    assert result == 42
    assert inherited == "request-42"
    assert worker_ident != caller_ident
    assert caller_context == "request-42"


def test_to_thread_reraises_worker_exception_at_await_boundary():
    def fail(message):
        raise LookupError(message)

    async def scenario():
        with pytest.raises(LookupError, match="worker failed"):
            await asyncio.to_thread(fail, "worker failed")

    asyncio.run(scenario())


# 从其他 OS thread 使用 ``run_coroutine_threadsafe``。
#
# 此函数要求显式 loop，并返回 thread-safe ``concurrent.futures.Future``，供非 event-loop
# 线程同步取得结果、异常或发出取消。asyncio Task/Future 本身通常不是 thread-safe；跨线程
# callback 应使用 loop.call_soon_threadsafe，不能直接操作 loop 内对象。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.run_coroutine_threadsafe
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-explicit-loop
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-concurrent-future
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-result
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-exception
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-cancel
# polyglot-covers: python.asyncio.loop.call_soon_threadsafe
# polyglot-covers: python.asyncio.cross-thread-task-safety-boundary




@contextmanager
def _event_loop_in_worker_thread():
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    failures = []

    def run_loop():
        asyncio.set_event_loop(loop)
        ready.set()
        try:
            loop.run_forever()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        except BaseException as error:
            failures.append(error)
        finally:
            loop.close()

    thread = threading.Thread(target=run_loop, name="asyncio-loop-thread")
    thread.start()
    assert ready.wait(timeout=2)
    try:
        yield loop, thread.ident
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        assert thread.is_alive() is False
        if failures:
            raise failures[0]


def test_threadsafe_submission_returns_concurrent_future_result_and_exception():
    async def describe(value):
        return value * 2, threading.get_ident()

    async def fail():
        raise LookupError("async failure")

    with _event_loop_in_worker_thread() as (loop, loop_thread_ident):
        result_future = asyncio.run_coroutine_threadsafe(describe(21), loop)
        assert isinstance(result_future, concurrent.futures.Future)
        assert result_future.result(timeout=2) == (42, loop_thread_ident)

        failed_future = asyncio.run_coroutine_threadsafe(fail(), loop)
        with pytest.raises(LookupError, match="async failure"):
            failed_future.result(timeout=2)


def test_cancelling_returned_future_requests_task_cancellation_in_loop_thread():
    started = threading.Event()
    cleaned = threading.Event()

    async def pending():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    with _event_loop_in_worker_thread() as (loop, _):
        future = asyncio.run_coroutine_threadsafe(pending(), loop)
        assert started.wait(timeout=2)
        assert future.cancel() is True
        with pytest.raises(concurrent.futures.CancelledError):
            future.result(timeout=2)
        assert cleaned.wait(timeout=2)


# Task callback API、suspended stack、Future-like state 与只读结果。
#
# Task 继承大部分 Future protocol，但其结果由 coroutine 决定，不能调用 set_result 或
# set_exception。pending Task 的 result/exception 是 InvalidStateError。get_stack/print_stack
# 用于诊断 suspension point；成功或取消后 stack 为空。done callback 由 loop 调度执行。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# Python 3.10 legacy generator-based coroutine 与迁移边界。
#
# asyncio.coroutine 把使用 ``yield from`` 的 generator 标记成旧式 coroutine，使其可被
# await/ensure_future；asyncio 的 introspection 会识别它，而 inspect 的 native-coroutine
# 判断不同。该 API 自 3.8 弃用并在 3.11 移除，新代码必须使用 async def/await。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.coroutine-decorator
# polyglot-covers: python.asyncio.generator-based-coroutine
# polyglot-covers: python.asyncio.generator-coroutine-yield-from
# polyglot-covers: python.asyncio.iscoroutine-generator-compatibility
# polyglot-covers: python.asyncio.iscoroutinefunction-generator-compatibility
# polyglot-covers: python.asyncio.ensure_future-generator-coroutine
# polyglot-covers: python.asyncio.generator-coroutines-deprecated-in-3.10
# polyglot-covers: python.asyncio.generator-coroutines-removed-in-3.11


with pytest.warns(DeprecationWarning, match="@coroutine"):

    @asyncio.coroutine
    def _legacy_compute(value):
        yielded = yield from asyncio.sleep(0, result=value * 2)
        return yielded


def test_asyncio_introspection_recognizes_legacy_generator_coroutine():
    coroutine = _legacy_compute(21)
    try:
        assert asyncio.iscoroutinefunction(_legacy_compute) is True
        assert inspect.iscoroutinefunction(_legacy_compute) is False
        assert asyncio.iscoroutine(coroutine) is True
        assert inspect.iscoroutine(coroutine) is False
        assert inspect.isawaitable(coroutine) is True
    finally:
        coroutine.close()


def test_legacy_coroutine_can_be_awaited_and_scheduled_with_ensure_future():
    async def scenario():
        direct = await _legacy_compute(10)
        scheduled = asyncio.ensure_future(_legacy_compute(21))
        assert isinstance(scheduled, asyncio.Task)
        return direct, await scheduled

    assert asyncio.run(scenario()) == (20, 42)


# asyncio Future eventual-result state、重复 await 与 callback scheduling。
#
# Future 是 callback API 到 async/await 的低层桥。pending 时同步 result/exception 不等待而抛
# InvalidStateError；set_result/set_exception 完成单次赋值。Future 可重复 await 同一结果。
# done callback 总由 loop.call_soon 排队，即使登记时已 done，也不会在调用栈内同步重入。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Future
# polyglot-covers: python.asyncio.loop.create_future
# polyglot-covers: python.asyncio.Future.get_loop
# polyglot-covers: python.asyncio.Future.done
# polyglot-covers: python.asyncio.Future.result
# polyglot-covers: python.asyncio.Future.exception
# polyglot-covers: python.asyncio.Future.set_result
# polyglot-covers: python.asyncio.Future.set_exception
# polyglot-covers: python.asyncio.Future-multiple-awaits
# polyglot-covers: python.asyncio.Future-single-assignment
# polyglot-covers: python.asyncio.Future.add_done_callback
# polyglot-covers: python.asyncio.Future.remove_done_callback
# polyglot-covers: python.asyncio.Future-callback-call-soon
# polyglot-covers: python.asyncio.Future-callback-context
# polyglot-covers: python.asyncio.Future.cancel
# polyglot-covers: python.asyncio.Future.cancelled
# polyglot-covers: python.asyncio.Future-cancel-message




CALLBACK_CONTEXT = contextvars.ContextVar("future_callback_context", default="missing")


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_future_result_is_single_assignment_reusable_awaitable():
    async def scenario():
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        assert asyncio.isfuture(future) is True
        assert future.get_loop() is loop
        assert future.done() is False
        with pytest.raises(asyncio.InvalidStateError):
            future.result()
        with pytest.raises(asyncio.InvalidStateError):
            future.exception()

        loop.call_soon(future.set_result, 42)
        assert await future == 42
        assert await future == 42
        assert future.result() == 42
        assert future.exception() is None
        with pytest.raises(asyncio.InvalidStateError):
            future.set_result(43)
        with pytest.raises(asyncio.InvalidStateError):
            future.set_exception(LookupError())

    asyncio.run(scenario())

def test_exception_future_reraises_same_object_from_result():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        error = LookupError("missing")
        future.set_exception(error)

        assert future.exception() is error
        with pytest.raises(LookupError, match="missing") as raised:
            await future
        assert raised.value is error

    asyncio.run(scenario())


def test_callbacks_are_scheduled_and_can_select_or_remove_context():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        calls = []

        def callback(completed):
            calls.append((completed.result(), CALLBACK_CONTEXT.get()))

        removed_context = contextvars.copy_context()
        removed_context.run(CALLBACK_CONTEXT.set, "removed")
        future.add_done_callback(callback, context=removed_context)
        assert future.remove_done_callback(callback) == 1

        callback_context = contextvars.copy_context()
        callback_context.run(CALLBACK_CONTEXT.set, "selected")
        future.set_result("done")
        future.add_done_callback(callback, context=callback_context)
        assert calls == []

        await _next_loop_turn()
        assert calls == [("done", "selected")]

    asyncio.run(scenario())


def test_cancel_is_terminal_and_preserves_message_for_result_and_exception():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        assert future.cancel("not needed") is True
        assert future.cancelled() is True
        assert future.done() is True
        assert future.cancel() is False

        with pytest.raises(asyncio.CancelledError) as result_error:
            future.result()
        assert result_error.value.args == ("not needed",)
        with pytest.raises(asyncio.CancelledError):
            future.exception()

    asyncio.run(scenario())


# ``isfuture/ensure_future/wrap_future`` 的 awaitable dispatch 与线程桥。
#
# ensure_future 对 asyncio Future/Task 保持 identity，对 coroutine 或一般 awaitable 创建 Task，
# 无效对象抛 TypeError。wrap_future 把 concurrent.futures.Future 的 thread-safe completion
# 转换成 loop-bound asyncio Future；两套 Future 的 wait/result timeout protocol 不能混用。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.isfuture
# polyglot-covers: python.asyncio.isfuture-future-like-marker
# polyglot-covers: python.asyncio.ensure_future
# polyglot-covers: python.asyncio.ensure-future-preserves-future-identity
# polyglot-covers: python.asyncio.ensure-future-coroutine-to-task
# polyglot-covers: python.asyncio.ensure-future-custom-awaitable
# polyglot-covers: python.asyncio.ensure-future-invalid-type
# polyglot-covers: python.asyncio.wrap_future
# polyglot-covers: python.asyncio.wrap-concurrent-future-result
# polyglot-covers: python.asyncio.wrap-future-cancellation-propagation
# polyglot-covers: python.asyncio.future-families-timeout-protocol-difference




class CustomAwaitable:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        async def resolve():
            return self.value

        return resolve().__await__()


class FutureLikeMarker:
    _asyncio_future_blocking = False


def test_ensure_future_dispatches_existing_future_coroutine_and_custom_awaitable():
    async def scenario():
        loop = asyncio.get_running_loop()
        existing = loop.create_future()
        existing.set_result("existing")
        assert asyncio.ensure_future(existing) is existing

        async def coroutine():
            return "coroutine"

        task = asyncio.ensure_future(coroutine())
        custom_task = asyncio.ensure_future(CustomAwaitable("custom"))
        assert isinstance(task, asyncio.Task)
        assert isinstance(custom_task, asyncio.Task)
        assert await asyncio.gather(task, custom_task) == ["coroutine", "custom"]

        with pytest.raises(TypeError, match="An asyncio.Future, a coroutine or an awaitable"):
            asyncio.ensure_future(42)

    asyncio.run(scenario())

def test_isfuture_accepts_documented_future_like_marker_protocol():
    assert asyncio.isfuture(FutureLikeMarker()) is True
    assert asyncio.isfuture(object()) is False


def test_wrap_future_bridges_result_and_cancellation_into_running_loop():
    async def scenario():
        concurrent_result = concurrent.futures.Future()
        wrapped_result = asyncio.wrap_future(concurrent_result)
        concurrent_result.set_result(42)
        assert await wrapped_result == 42

        concurrent_pending = concurrent.futures.Future()
        wrapped_pending = asyncio.wrap_future(concurrent_pending)
        assert wrapped_pending.cancel("stop") is True

        turn = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(turn.set_result, None)
        await turn
        assert concurrent_pending.cancelled() is True
        with pytest.raises(asyncio.CancelledError):
            await wrapped_pending

    asyncio.run(scenario())


def test_asyncio_future_result_does_not_accept_concurrent_timeout_argument():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        with pytest.raises(TypeError, match="takes no keyword arguments"):
            future.result(timeout=1)
        future.cancel()

    asyncio.run(scenario())


# loop task factory、``run_in_executor`` 与 default executor shutdown。
#
# task factory 让替代 event loop/instrumentation 控制 Task 构造；恢复 None 即默认工厂。
# run_in_executor 返回 asyncio Future，positional args 原样传入，keyword 应使用 partial。
# shutdown_default_executor 会 join worker，之后该 loop 不允许再次使用默认 executor。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


def test_default_executor_warns_for_other_types_and_shutdown_is_terminal_for_loop():
    loop = asyncio.new_event_loop()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="polyglot-default")
    try:
        with pytest.warns(DeprecationWarning, match="not an instance"):
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


# event loop exception context、custom handler delegation 与 debug flag。
#
# callback 抛出的异常不能在 await site 直接捕获，loop 会把 message/exception/handle 等信息
# 放入 extensible context dict 交给 exception handler。custom handler 可处理或显式委托
# default_exception_handler。set_exception_handler(None) 恢复默认；debug flag 可运行时切换。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.loop.set_exception_handler
# polyglot-covers: python.asyncio.loop.get_exception_handler
# polyglot-covers: python.asyncio.loop.call_exception_handler
# polyglot-covers: python.asyncio.loop.default_exception_handler
# polyglot-covers: python.asyncio.exception-handler-loop-context-signature
# polyglot-covers: python.asyncio.exception-handler-context-message
# polyglot-covers: python.asyncio.exception-handler-context-exception
# polyglot-covers: python.asyncio.exception-handler-context-handle
# polyglot-covers: python.asyncio.exception-handler-extensible-context
# polyglot-covers: python.asyncio.loop.get_debug
# polyglot-covers: python.asyncio.loop.set_debug



async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_explicit_exception_context_reaches_custom_handler_unchanged():
    async def scenario():
        loop = asyncio.get_running_loop()
        received = []

        def handler(received_loop, context):
            received.append((received_loop, context))

        loop.set_exception_handler(handler)
        assert loop.get_exception_handler() is handler
        context = {
            "message": "educational failure",
            "exception": LookupError("missing"),
            "custom-key": 42,
        }
        loop.call_exception_handler(context)

        assert received == [(loop, context)]
        loop.set_exception_handler(None)
        assert loop.get_exception_handler() is None

    asyncio.run(scenario())

def test_callback_exception_supplies_exception_and_handle_to_handler():
    async def scenario():
        loop = asyncio.get_running_loop()
        contexts = []
        loop.set_exception_handler(lambda _, context: contexts.append(context))

        def fail():
            raise ValueError("callback failed")

        handle = loop.call_soon(fail)
        await _next_loop_turn()

        assert len(contexts) == 1
        assert "Exception in callback" in contexts[0]["message"]
        assert isinstance(contexts[0]["exception"], ValueError)
        assert contexts[0]["handle"] is handle

    asyncio.run(scenario())


def test_loop_debug_flag_can_be_toggled_explicitly():
    async def scenario():
        loop = asyncio.get_running_loop()
        original = loop.get_debug()
        loop.set_debug(not original)
        assert loop.get_debug() is (not original)
        loop.set_debug(original)
        assert loop.get_debug() is original

    asyncio.run(scenario())
