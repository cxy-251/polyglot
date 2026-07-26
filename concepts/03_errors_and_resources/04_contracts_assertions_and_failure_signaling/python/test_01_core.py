"""契约、断言与失败信号。

共同问题：开发期断言与输入校验如何区分；哪些约束能在编译期表达；
调用方如何精确检查失败类型和内容。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/python/language/test_009_exception_handling_and_chaining.py

import pytest


def positive_port(value):
    if not isinstance(value, int):
        raise TypeError("port must be an integer")
    if value <= 0:
        raise ValueError("port must be positive")
    return value


def test_assertion_reports_broken_internal_assumption():
    with pytest.raises(AssertionError, match="state must be ready"):
        assert False, "state must be ready"


def test_runtime_validation_uses_stable_exception_categories():
    assert positive_port(8080) == 8080

    with pytest.raises(TypeError, match="integer"):
        positive_port("8080")
    with pytest.raises(ValueError, match="positive"):
        positive_port(0)


def test_assert_is_not_a_public_input_validation_boundary():
    assert __debug__ is True

    # `python -O` 会删除 assert；公共 API 必须显式 raise，而不是依赖当前解释器优化模式。


def test_python_type_annotations_do_not_enforce_calls_at_runtime():
    def double(value: int) -> int:
        return value * 2

    assert double(3) == 6
    assert double("a") == "aa"

    # 与 C++ concepts/static_assert 不同，普通 Python 注解只提供元数据，检查需要额外工具。

