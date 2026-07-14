"""308｜event loop 安装 Unix signal callback。

add_signal_handler 的 callback 由 loop 像普通 callback 一样调度，因此可以安全地操作 Future；
它比 signal.signal 的最小异步信号处理函数更易组合。注册必须在主线程完成。remove 返回 bool，
案例始终恢复原 handler，避免向其他测试泄漏进程级状态。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.add_signal_handler
# polyglot-covers: python.asyncio.signal-handler-loop-scheduled-callback
# polyglot-covers: python.asyncio.signal-handler-callback-args
# polyglot-covers: python.asyncio.signal-handler-main-thread-only
# polyglot-covers: python.asyncio.loop.remove_signal_handler
# polyglot-covers: python.asyncio.remove-signal-handler-return-value
# polyglot-covers: python.asyncio.signal-handler-process-state-restoration

import asyncio
import os
import signal


def test_signal_handler_can_resolve_a_future_and_is_then_removed():
    async def scenario():
        loop = asyncio.get_running_loop()
        previous = signal.getsignal(signal.SIGUSR1)
        received = loop.create_future()

        try:
            loop.add_signal_handler(
                signal.SIGUSR1,
                received.set_result,
                "SIGUSR1 received",
            )
            os.kill(os.getpid(), signal.SIGUSR1)
            assert await received == "SIGUSR1 received"
            assert loop.remove_signal_handler(signal.SIGUSR1) is True
            assert loop.remove_signal_handler(signal.SIGUSR1) is False
        finally:
            loop.remove_signal_handler(signal.SIGUSR1)
            signal.signal(signal.SIGUSR1, previous)

    asyncio.run(scenario())
