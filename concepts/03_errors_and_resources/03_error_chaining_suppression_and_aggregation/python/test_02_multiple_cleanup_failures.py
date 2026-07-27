"""多个清理失败的保留方式。

共同问题：主体失败后多个清理也失败时，哪个错误成为最外层；其余失败如何保留；
没有内置聚合协议时如何显式保存全部结果。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/python/language/test_009_exception_handling_and_chaining.py
# polyglot-related: languages/python/language/test_010_context_manager_protocols.py

from contextlib import ExitStack

import pytest


class FailingExit:
    def __init__(self, name, events):
        self.name = name
        self.events = events

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.events.append(f"exit:{self.name}")
        raise RuntimeError(self.name)


def test_exit_stack_runs_every_exit_and_links_failures_in_lifo_order():
    events = []
    body_error = ValueError("body")

    with pytest.raises(RuntimeError, match="first") as caught:
        with ExitStack() as stack:
            stack.enter_context(FailingExit("first", events))
            stack.enter_context(FailingExit("second", events))
            raise body_error

    first_error = caught.value
    second_error = first_error.__context__

    assert events == ["exit:second", "exit:first"]
    assert isinstance(second_error, RuntimeError)
    assert str(second_error) == "second"
    assert second_error.__context__ is body_error

    # Python 3.10 没有 ExceptionGroup；ExitStack 仍执行全部回调，并通过异常 context 链
    # 保留失败顺序，但调用方不能用 except* 独立匹配其中的错误。
