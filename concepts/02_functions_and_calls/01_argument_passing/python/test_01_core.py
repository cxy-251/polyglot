"""横向概念 003｜参数绑定、对象传递与默认值。

共同问题：缺少或多余实参如何处理；修改与重新绑定是否影响调用者；
默认表达式何时求值；如何表达命名选项和可变参数。
"""

# polyglot-family: functions_and_calls
# polyglot-concept: argument_passing
# polyglot-related: languages/python/language/test_006_functions_calls_and_argument_binding.py

import pytest


def test_signature_binding_rejects_missing_and_extra_arguments():
    def pair(first, second):
        return first, second

    assert pair("a", "b") == ("a", "b")
    assert pair(second="b", first="a") == ("a", "b")

    with pytest.raises(TypeError):
        pair("a")
    with pytest.raises(TypeError):
        pair("a", "b", "c")


def test_mutation_is_visible_but_parameter_rebinding_is_local():
    original = ["before"]

    def mutate_then_rebind(value):
        value.append("mutated")
        value = ["replacement"]
        return value

    replacement = mutate_then_rebind(original)

    assert original == ["before", "mutated"]
    assert replacement == ["replacement"]


def test_default_object_is_created_once_when_def_executes():
    def remember(value, history=[]):
        history.append(value)
        return history

    first = remember("first")
    second = remember("second")

    assert first is second
    assert second == ["first", "second"]


def test_star_parameters_collect_positional_and_named_arguments():
    def collect(required, *extra, **options):
        return required, extra, options

    assert collect("task", 1, 2, urgent=True) == (
        "task",
        (1, 2),
        {"urgent": True},
    )
