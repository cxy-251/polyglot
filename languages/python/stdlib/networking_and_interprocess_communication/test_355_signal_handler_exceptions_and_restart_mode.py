"""355｜处理器异常的主线程传播与 siginterrupt restart 模式。

底层 C handler 只设置标记；Python 回调稍后在主线程字节码边界执行。若回调抛异常，该异常会像
“凭空”出现在主线程任意字节码处，可能打断尚未建立好的不变量。高可靠服务通常让 handler 只写
wakeup fd/设置标志，而不直接抛异常。siginterrupt 控制被信号打断的系统调用是否自动重启。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.handler-exception-propagates-main-thread
# polyglot-covers: python.signal.handler-exception-bytecode-boundary-trap
# polyglot-covers: python.signal.siginterrupt
# polyglot-covers: python.signal.siginterrupt-false-restarts-syscalls
# polyglot-covers: python.signal.siginterrupt-true-interrupts-syscalls
# polyglot-covers: python.signal.installing-handler-resets-interrupt-mode

import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1") or not hasattr(signal, "siginterrupt"),
    reason="siginterrupt 是 Unix API",
)


class HandlerRaised(RuntimeError):
    pass


def test_exception_raised_by_handler_propagates_from_raise_signal():
    def handler(signum, frame):
        raise HandlerRaised(signum)

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, handler)
        with pytest.raises(HandlerRaised) as raised:
            signal.raise_signal(signal.SIGUSR1)
        assert raised.value.args == (signal.SIGUSR1,)
    finally:
        signal.signal(signal.SIGUSR1, previous)


def test_siginterrupt_switches_restart_policy_without_a_query_api():
    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, lambda signum, frame: None)
        # signal() 隐式把该信号设成 interruptible；False 改为自动重启，True 再改回来。
        assert signal.siginterrupt(signal.SIGUSR1, False) is None
        assert signal.siginterrupt(signal.SIGUSR1, True) is None
    finally:
        # 重新安装旧 handler 也会重置 restart 策略；模块没有对应 getter 可保存该隐式状态。
        signal.signal(signal.SIGUSR1, previous)
