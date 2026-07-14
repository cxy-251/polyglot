"""309｜process-wide event loop policy、per-thread current loop 与 Unix child watcher。

Policy 决定 get/set/new_event_loop 的行为；对象本身全进程共享，但默认 current loop 按线程隔离。
自定义实现宜继承 DefaultEventLoopPolicy，仅覆写需要改变的方法。Unix child watcher 负责把子进程
退出转成 loop callback；不同 watcher 在线程、signal 干扰、复杂度和平台支持之间取舍。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.get_event_loop_policy
# polyglot-covers: python.asyncio.set_event_loop_policy
# polyglot-covers: python.asyncio.AbstractEventLoopPolicy
# polyglot-covers: python.asyncio.DefaultEventLoopPolicy
# polyglot-covers: python.asyncio.policy-process-wide-object
# polyglot-covers: python.asyncio.policy-current-loop-per-thread-default
# polyglot-covers: python.asyncio.policy.get_event_loop
# polyglot-covers: python.asyncio.policy.set_event_loop
# polyglot-covers: python.asyncio.policy.new_event_loop
# polyglot-covers: python.asyncio.custom-policy-subclass-default
# polyglot-covers: python.asyncio.SelectorEventLoop
# polyglot-covers: python.asyncio.selector-event-loop-custom-selector
# polyglot-covers: python.asyncio.AbstractChildWatcher
# polyglot-covers: python.asyncio.get_child_watcher
# polyglot-covers: python.asyncio.ThreadedChildWatcher
# polyglot-covers: python.asyncio.MultiLoopChildWatcher
# polyglot-covers: python.asyncio.SafeChildWatcher
# polyglot-covers: python.asyncio.FastChildWatcher
# polyglot-covers: python.asyncio.PidfdChildWatcher
# polyglot-covers: python.asyncio.child-watcher-strategy-tradeoffs

import asyncio
import selectors


class CountingSelectorPolicy(asyncio.DefaultEventLoopPolicy):
    def __init__(self):
        super().__init__()
        self.created = 0

    def new_event_loop(self):
        self.created += 1
        # 显式 selector 的写法适合需要可预测 selector 实现的框架或诊断环境。
        return asyncio.SelectorEventLoop(selectors.SelectSelector())


def test_custom_policy_controls_loop_creation_and_current_loop_lookup():
    previous_policy = asyncio.get_event_loop_policy()
    policy = CountingSelectorPolicy()
    loop = None
    try:
        asyncio.set_event_loop_policy(policy)
        assert asyncio.get_event_loop_policy() is policy
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        assert policy.created == 1
        assert asyncio.get_event_loop() is loop
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        asyncio.set_event_loop(None)
        if loop is not None:
            loop.close()
        asyncio.set_event_loop_policy(previous_policy)


def test_default_unix_child_watcher_implements_the_abstract_contract():
    watcher = asyncio.get_child_watcher()
    assert isinstance(watcher, asyncio.AbstractChildWatcher)
    assert watcher.is_active() is True

    # 这些都是 Python 3.10 提供的策略类；不实际替换全局 watcher，以免干扰其他测试。
    implementations = [
        asyncio.ThreadedChildWatcher,
        asyncio.MultiLoopChildWatcher,
        asyncio.SafeChildWatcher,
        asyncio.FastChildWatcher,
        asyncio.PidfdChildWatcher,
    ]
    assert all(issubclass(item, asyncio.AbstractChildWatcher) for item in implementations)
