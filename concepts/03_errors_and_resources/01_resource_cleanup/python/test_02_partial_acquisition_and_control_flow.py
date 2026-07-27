"""资源部分取得失败与控制流退出。

共同问题：后续资源取得失败时已取得资源是否清理；return 是否绕过清理；
清理责任何时登记，尚未成功取得的资源是否参与释放。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/python/language/test_010_context_manager_protocols.py

from contextlib import ExitStack

import pytest


class Resource:
    def __init__(self, name, events, *, fail_on_enter=False):
        self.name = name
        self.events = events
        self.fail_on_enter = fail_on_enter

    def __enter__(self):
        self.events.append(f"enter:{self.name}")
        if self.fail_on_enter:
            raise RuntimeError(f"cannot acquire {self.name}")
        return self

    def __exit__(self, *_):
        self.events.append(f"exit:{self.name}")


def test_exit_stack_cleans_registered_resources_after_later_acquisition_fails():
    events = []

    with pytest.raises(RuntimeError, match="second"):
        with ExitStack() as stack:
            stack.enter_context(Resource("first", events))
            stack.enter_context(Resource("second", events, fail_on_enter=True))

    assert events == ["enter:first", "enter:second", "exit:first"]

    # enter_context 只在 __enter__ 成功后登记 __exit__；失败的 second 没有取得完成，
    # 已登记的 first 则由 ExitStack 在异常路径逆序释放。


def test_return_from_with_still_runs_exit_before_value_reaches_caller():
    events = []

    def work():
        with Resource("value", events):
            events.append("return")
            return 42

    result = work()

    assert result == 42
    assert events == ["enter:value", "return", "exit:value"]
