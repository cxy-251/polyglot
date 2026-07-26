"""生成器、惰性与提前终止。

共同问题：何时执行生产逻辑；如何限制消费；提前终止是否运行清理；
惰性管道能否重复使用。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/python/language/test_008_iteration_and_generator_protocols.py

import itertools


def test_generator_body_starts_only_when_consumed():
    events = []

    def values():
        events.append("start")
        yield 1
        events.append("resume")
        yield 2

    iterator = values()
    assert events == []
    assert next(iterator) == 1
    assert events == ["start"]


def test_islice_limits_an_unbounded_lazy_source():
    numbers = itertools.count(10, 2)

    assert list(itertools.islice(numbers, 3)) == [10, 12, 14]
    assert next(numbers) == 16


def test_generator_close_runs_finally_at_the_suspension_point():
    events = []

    def values():
        try:
            yield 1
            yield 2
        finally:
            events.append("closed")

    iterator = values()
    assert next(iterator) == 1
    iterator.close()

    assert events == ["closed"]


def test_generator_expression_is_single_pass_and_composes_lazily():
    calls = []
    doubled = (calls.append(value) or value * 2 for value in range(3))

    assert next(doubled) == 0
    assert calls == [0]
    assert list(doubled) == [2, 4]
    assert list(doubled) == []

