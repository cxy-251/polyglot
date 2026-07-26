"""同步迭代协议。

共同问题：如何取得迭代器；推进与完成如何表示；迭代器能否复用；
提前退出是否自动触发关闭协议。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/python/language/test_008_iteration_and_generator_protocols.py

import pytest


class Countdown:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current == 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value


def test_iter_and_next_expose_the_protocol_directly():
    iterator = iter(Countdown(2))

    assert next(iterator) == 2
    assert next(iterator) == 1
    with pytest.raises(StopIteration):
        next(iterator)


def test_container_is_reiterable_but_iterator_is_single_pass():
    values = [1, 2]
    iterator = iter(values)

    assert list(values) == [1, 2]
    assert list(values) == [1, 2]
    assert list(iterator) == [1, 2]
    assert list(iterator) == []


def test_for_loop_translates_stop_iteration_into_normal_completion():
    assert [value for value in Countdown(3)] == [3, 2, 1]


def test_break_does_not_call_arbitrary_iterator_close_method():
    events = []

    class Closable(Countdown):
        def close(self):
            events.append("close")

    for _ in Closable(2):
        break

    assert events == []
    # JavaScript IteratorClose 会在 for-of 提前退出时调用 return；Python for 不调用任意 close。

