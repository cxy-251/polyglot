"""可调用对象适配与偏应用。

共同问题：如何预绑定参数；包装器如何保留调用契约；如何统一不同 callable；
适配器是否复制还是引用状态。
"""

# polyglot-family: functions_and_calls
# polyglot-concept: callable_adaptation_and_partial_application
# polyglot-related: languages/python/language/test_006_functions_calls_and_argument_binding.py

import functools
import inspect
import operator


def test_partial_prebinds_selected_positional_and_keyword_arguments():
    def describe(prefix, value, *, suffix):
        return f"{prefix}{value}{suffix}"

    bracket = functools.partial(describe, "[", suffix="]")

    assert bracket("value") == "[value]"
    assert bracket.func is describe
    assert bracket.args == ("[",)
    assert bracket.keywords == {"suffix": "]"}


def test_wraps_preserves_user_facing_function_metadata():
    def trace(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper

    @trace
    def add(left: int, right: int = 0) -> int:
        """Add two values."""
        return left + right

    assert add(2, right=3) == 5
    assert add.__name__ == "add"
    assert inspect.signature(add) == inspect.signature(add.__wrapped__)


def test_callable_objects_and_functions_share_one_invocation_surface():
    class Scale:
        def __init__(self, factor):
            self.factor = factor

        def __call__(self, value):
            return value * self.factor

    operations = [abs, Scale(3), functools.partial(operator.add, 2)]

    assert [operation(-2) for operation in operations] == [2, -6, 0]


def test_partial_holds_references_to_mutable_arguments():
    options = {"prefix": "a"}

    def read(mapping):
        return mapping["prefix"]

    adapted = functools.partial(read, options)
    options["prefix"] = "b"

    assert adapted() == "b"
