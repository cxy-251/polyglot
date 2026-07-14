"""290｜``call_soon/call_later/call_at``、Handle cancellation 与 callback Context。

call_soon 以登记顺序在下一轮执行且 exactly once；Handle.cancel 只能阻止尚未执行的 callback。
delayed callback 使用 loop monotonic time，返回 TimerHandle；同一绝对时刻的相对顺序未定义。
callback 默认复制当前 Context，也可显式传 context。keyword args 应用 functools.partial 绑定。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.call_soon
# polyglot-covers: python.asyncio.call-soon-registration-order
# polyglot-covers: python.asyncio.call-soon-exactly-once
# polyglot-covers: python.asyncio.Handle
# polyglot-covers: python.asyncio.Handle.cancel
# polyglot-covers: python.asyncio.Handle.cancelled
# polyglot-covers: python.asyncio.callback-context-copy
# polyglot-covers: python.asyncio.callback-explicit-context
# polyglot-covers: python.asyncio.callback-keywords-via-partial
# polyglot-covers: python.asyncio.loop.call_later
# polyglot-covers: python.asyncio.loop.call_at
# polyglot-covers: python.asyncio.loop.time
# polyglot-covers: python.asyncio.TimerHandle
# polyglot-covers: python.asyncio.TimerHandle.when
# polyglot-covers: python.asyncio.equal-time-callback-order-undefined

import asyncio
import contextvars
from functools import partial


CALLBACK_VALUE = contextvars.ContextVar("asyncio_callback_value", default="missing")


def test_call_soon_preserves_order_cancels_handle_and_uses_selected_context():
    loop = asyncio.new_event_loop()
    calls = []

    def record(label, *, suffix=""):
        calls.append((label + suffix, CALLBACK_VALUE.get()))

    copied_token = CALLBACK_VALUE.set("copied-at-schedule")
    try:
        first = loop.call_soon(record, "first")
        cancelled = loop.call_soon(record, "cancelled")
        cancelled.cancel()

        explicit = contextvars.Context()
        explicit.run(CALLBACK_VALUE.set, "explicit")
        loop.call_soon(
            partial(record, "with", suffix=" keywords"),
            context=explicit,
        )
        CALLBACK_VALUE.set("changed-after-schedule")
        loop.call_soon(loop.stop)
        loop.run_forever()
    finally:
        CALLBACK_VALUE.reset(copied_token)
        loop.close()
    assert isinstance(first, asyncio.Handle)
    assert first.cancelled() is False
    assert cancelled.cancelled() is True
    assert calls == [
        ("first", "copied-at-schedule"),
        ("with keywords", "explicit"),
    ]


def test_zero_delay_and_current_time_timers_run_without_wall_clock_wait():
    loop = asyncio.new_event_loop()
    calls = []
    try:
        now = loop.time()
        later = loop.call_later(0, calls.append, "relative")
        absolute = loop.call_at(now, calls.append, "absolute")
        cancelled = loop.call_at(now, calls.append, "cancelled")
        cancelled.cancel()
        loop.call_later(0, loop.stop)

        loop.run_forever()

        assert isinstance(later, asyncio.TimerHandle)
        assert isinstance(absolute, asyncio.TimerHandle)
        assert later.when() >= now
        assert absolute.when() == now
        # 两个 deadline 相同或已经到期；规范不承诺它们之间的执行顺序。
        assert sorted(calls) == ["absolute", "relative"]
        assert cancelled.cancelled() is True
    finally:
        loop.close()
