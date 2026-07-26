"""可调用对象绑定与调用上下文。

共同问题：成员函数如何获得接收者；提取函数后是否保留接收者；如何显式调用；
语言是否允许固定或替换调用上下文。
"""

# polyglot-family: functions_and_calls
# polyglot-concept: callable_binding_and_invocation_context
# polyglot-related: languages/python/language/test_007_attribute_access_and_descriptors.py
# polyglot-related: languages/python/language/test_011_classes_construction_and_inheritance.py

import inspect

import pytest


class Counter:
    category = "counter"

    def __init__(self, value):
        self.value = value

    def add(self, amount):
        return self.value + amount

    @classmethod
    def describe(cls):
        return cls.category

    @staticmethod
    def identity(value):
        return value


def test_instance_attribute_access_creates_a_bound_method():
    counter = Counter(10)
    bound = counter.add

    assert inspect.ismethod(bound)
    assert bound.__self__ is counter
    assert bound(2) == 12


def test_class_attribute_is_unbound_function_and_needs_explicit_instance():
    counter = Counter(10)

    assert inspect.isfunction(Counter.add)
    assert Counter.add(counter, 2) == 12
    with pytest.raises(TypeError):
        Counter.add(2)


def test_bound_method_keeps_its_original_receiver_when_stored():
    first = Counter(10)
    second = Counter(20)
    stored = first.add

    assert stored(1) == 11
    assert second.add(1) == 21

    # 与 JavaScript 的成员函数不同，提取 Python bound method 后不会丢失 self。


def test_classmethod_and_staticmethod_use_distinct_descriptor_rules():
    counter = Counter(10)

    assert counter.describe() == "counter"
    assert Counter.describe.__self__ is Counter
    assert counter.identity("value") == "value"
