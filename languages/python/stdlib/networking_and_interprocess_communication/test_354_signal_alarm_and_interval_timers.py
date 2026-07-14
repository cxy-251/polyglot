"""354｜alarm 与 setitimer 的调度、取消和旧值恢复。

alarm 只有整数秒且同一进程只有一个；再次调用会替换旧闹钟并返回其剩余整秒数。setitimer 支持
浮点延时、重复 interval 和三种计时来源，返回 ``(delay, interval)`` 旧值。测试只安排远期计时器
并立即取消，不依赖真实等待；finally 恢复调用前的全局计时器。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.alarm
# polyglot-covers: python.signal.alarm-replaces-previous
# polyglot-covers: python.signal.alarm-zero-cancels
# polyglot-covers: python.signal.alarm-integer-seconds
# polyglot-covers: python.signal.setitimer
# polyglot-covers: python.signal.getitimer
# polyglot-covers: python.signal.setitimer-float-seconds
# polyglot-covers: python.signal.setitimer-repeat-interval
# polyglot-covers: python.signal.setitimer-zero-cancels
# polyglot-covers: python.signal.setitimer-returns-old-values
# polyglot-covers: python.signal.ItimerError
# polyglot-covers: python.signal.ITIMER_REAL
# polyglot-covers: python.signal.ITIMER_VIRTUAL
# polyglot-covers: python.signal.ITIMER_PROF

import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "setitimer") or not hasattr(signal, "alarm"),
    reason="POSIX interval timer 在此平台不可用",
)


def test_alarm_replaces_one_process_wide_integer_timer_and_zero_cancels_it():
    previous_remaining = signal.alarm(0)
    try:
        assert signal.alarm(60) == 0
        remaining = signal.alarm(0)
        assert 1 <= remaining <= 60
        with pytest.raises(TypeError):
            signal.alarm(0.5)
    finally:
        if previous_remaining:
            signal.alarm(previous_remaining)


def test_interval_timer_exposes_float_delay_interval_and_previous_values():
    previous = signal.setitimer(signal.ITIMER_REAL, 0)
    try:
        assert signal.setitimer(signal.ITIMER_REAL, 60.5, 2.25) == (0.0, 0.0)
        delay, interval = signal.getitimer(signal.ITIMER_REAL)
        assert 0 < delay <= 60.5
        assert interval == pytest.approx(2.25)

        old_delay, old_interval = signal.setitimer(signal.ITIMER_REAL, 0)
        assert 0 < old_delay <= delay
        assert old_interval == pytest.approx(2.25)
        assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous)


def test_timer_kinds_and_invalid_kind_error_are_explicit():
    assert {
        signal.ITIMER_REAL,
        signal.ITIMER_VIRTUAL,
        signal.ITIMER_PROF,
    } == {0, 1, 2}
    with pytest.raises(signal.ItimerError):
        signal.getitimer(-1)
    assert issubclass(signal.ItimerError, OSError)
