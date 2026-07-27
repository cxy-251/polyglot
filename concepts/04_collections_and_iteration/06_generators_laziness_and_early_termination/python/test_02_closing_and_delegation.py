"""提前终止的关闭协议与委托。

共同问题：消费方提前停止时是否通知生产方；清理如何穿过委托层；
关闭失败如何传播给消费方。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/python/language/test_008_iteration_and_generator_protocols.py

import pytest


def test_close_propagates_through_yield_from_and_runs_both_finally_blocks():
    events = []

    def inner():
        try:
            yield 1
            yield 2
        finally:
            events.append("inner closed")

    def outer():
        try:
            yield from inner()
        finally:
            events.append("outer closed")

    iterator = outer()
    assert next(iterator) == 1

    iterator.close()

    assert events == ["inner closed", "outer closed"]


def test_generator_must_not_yield_after_generator_exit():
    def invalid_cleanup():
        try:
            yield 1
        except GeneratorExit:
            yield 2

    iterator = invalid_cleanup()
    assert next(iterator) == 1

    with pytest.raises(RuntimeError, match="ignored GeneratorExit"):
        iterator.close()
    iterator.close()

    # close 注入 GeneratorExit；生成器可以清理并返回，但再次 yield 会被拒绝，避免生产方
    # 吞掉消费方的终止请求。清理代码仍应放在 finally 中。
