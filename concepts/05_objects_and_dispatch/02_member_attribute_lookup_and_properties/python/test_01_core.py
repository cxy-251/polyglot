"""成员、属性查找与 property。

共同问题：实例与类型成员的查找顺序是什么；访问器如何获得接收者；
数据描述符能否覆盖实例字典；缺失属性如何定制。
"""

# polyglot-family: objects_and_dispatch
# polyglot-concept: member_attribute_lookup_and_properties
# polyglot-related: languages/python/language/test_007_attribute_access_and_descriptors.py

import pytest


class Positive:
    def __set_name__(self, owner, name):
        self.storage_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.storage_name)

    def __set__(self, instance, value):
        if value <= 0:
            raise ValueError("must be positive")
        setattr(instance, self.storage_name, value)


class Product:
    price = Positive()

    def __init__(self, price):
        self.price = price

    @property
    def doubled(self):
        return self.price * 2

    def __getattr__(self, name):
        return f"missing:{name}"


def test_data_descriptor_controls_instance_read_and_write():
    product = Product(5)

    assert product.price == 5
    with pytest.raises(ValueError):
        product.price = 0


def test_data_descriptor_wins_over_same_named_instance_dictionary_entry():
    product = Product(5)
    product.__dict__["price"] = 99

    assert product.price == 5
    assert product.__dict__["price"] == 99


def test_property_is_a_descriptor_and_receives_the_instance():
    product = Product(5)

    assert product.doubled == 10
    with pytest.raises(AttributeError):
        product.doubled = 20


def test_getattr_runs_only_after_normal_lookup_fails():
    product = Product(5)

    assert product.price == 5
    assert product.unknown == "missing:unknown"

