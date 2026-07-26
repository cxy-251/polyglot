"""错误链、抑制与聚合。

共同问题：包装错误如何保留原因；隐式上下文能否隐藏；多个失败如何携带；
清理失败与主体失败如何同时保留。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/python/language/test_009_exception_handling_and_chaining.py

import builtins

import pytest


def test_raise_from_sets_an_explicit_cause():
    original = ValueError("invalid input")

    with pytest.raises(RuntimeError) as caught:
        try:
            raise original
        except ValueError as error:
            raise RuntimeError("load failed") from error

    assert caught.value.__cause__ is original
    assert caught.value.__suppress_context__ is True


def test_implicit_chaining_uses_context():
    original = ValueError("invalid input")

    with pytest.raises(RuntimeError) as caught:
        try:
            raise original
        except ValueError:
            raise RuntimeError("load failed")

    assert caught.value.__cause__ is None
    assert caught.value.__context__ is original


def test_from_none_hides_display_but_keeps_context_for_introspection():
    original = ValueError("invalid input")

    with pytest.raises(RuntimeError) as caught:
        try:
            raise original
        except ValueError:
            raise RuntimeError("public failure") from None

    assert caught.value.__suppress_context__ is True
    assert caught.value.__context__ is original


def test_cleanup_failure_becomes_primary_and_keeps_body_as_context():
    class FailingCleanup:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            raise RuntimeError("cleanup")

    with pytest.raises(RuntimeError) as caught:
        with FailingCleanup():
            raise ValueError("body")

    assert str(caught.value) == "cleanup"
    assert isinstance(caught.value.__context__, ValueError)


def test_python_310_has_no_builtin_exception_group():
    assert not hasattr(builtins, "ExceptionGroup")

    # Python 3.11 才增加 ExceptionGroup；锁定的 3.10 需要领域容器或第三方方案表达多错误。
