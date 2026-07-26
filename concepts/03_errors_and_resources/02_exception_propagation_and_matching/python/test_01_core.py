"""异常传播、匹配与重新抛出。

共同问题：抛出的值有什么类型约束；处理器如何匹配；重新抛出是否保留原对象；
清理和 finally 在传播路径上的顺序是什么。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/python/language/test_009_exception_handling_and_chaining.py

import pytest


class DomainError(RuntimeError):
    pass


def test_handler_matches_exception_subclasses():
    caught = []

    try:
        raise DomainError("failed")
    except ValueError:
        caught.append("value")
    except RuntimeError as error:
        caught.append(type(error).__name__)

    assert caught == ["DomainError"]


def test_bare_raise_preserves_the_same_exception_object():
    original = DomainError("failed")

    def propagate():
        try:
            raise original
        except DomainError:
            raise

    with pytest.raises(DomainError) as caught:
        propagate()

    assert caught.value is original


def test_finally_runs_before_the_exception_reaches_outer_handler():
    events = []

    try:
        try:
            events.append("body")
            raise DomainError("failed")
        finally:
            events.append("finally")
    except DomainError:
        events.append("caught")

    assert events == ["body", "finally", "caught"]


def test_only_base_exception_instances_or_classes_can_be_raised():
    with pytest.raises(TypeError):
        raise "failed"

    # JavaScript 可以 throw 任意值；Python 与 C++ 都要求异常属于各自的异常对象体系。


def test_exception_else_runs_only_when_try_body_completes_normally():
    events = []

    try:
        events.append("body")
    except DomainError:
        events.append("caught")
    else:
        events.append("else")

    assert events == ["body", "else"]
