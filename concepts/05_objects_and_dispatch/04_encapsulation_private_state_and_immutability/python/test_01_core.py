"""封装、私有状态与只读边界。

共同问题：私有成员由语法还是约定保护；只读是否深层生效；
调用方能否绕过封装；类型如何暴露受控更新。
"""

# polyglot-family: objects_and_dispatch
# polyglot-concept: encapsulation_private_state_and_immutability
# polyglot-related: languages/python/language/test_011_classes_construction_and_inheritance.py

import dataclasses

import pytest


class Account:
    def __init__(self, balance):
        self.__balance = balance

    @property
    def balance(self):
        return self.__balance

    def deposit(self, amount):
        self.__balance += amount


def test_double_underscore_uses_name_mangling_not_a_security_boundary():
    account = Account(10)

    assert account.balance == 10
    assert account._Account__balance == 10
    assert not hasattr(account, "__balance")


def test_read_only_property_blocks_normal_assignment():
    account = Account(10)

    with pytest.raises(AttributeError):
        account.balance = 20

    account.deposit(5)
    assert account.balance == 15


def test_frozen_dataclass_blocks_field_assignment():
    @dataclasses.dataclass(frozen=True)
    class Point:
        x: int
        tags: list

    point = Point(1, [])

    with pytest.raises(dataclasses.FrozenInstanceError):
        point.x = 2
    point.tags.append("mutable child")
    assert point.tags == ["mutable child"]


def test_immutability_wrappers_are_often_shallow():
    value = (["mutable"],)
    value[0].append("changed")

    assert value == (["mutable", "changed"],)
