"""继承、动态分派与 super。

共同问题：覆盖方法如何动态选择；基类实现如何调用；多继承顺序如何确定；
把派生对象当基类使用是否丢失动态类型。
"""

# polyglot-family: objects_and_dispatch
# polyglot-concept: inheritance_dynamic_dispatch_and_super
# polyglot-related: languages/python/language/test_011_classes_construction_and_inheritance.py


class Base:
    def describe(self):
        return ["base"]


class Left(Base):
    def describe(self):
        return ["left", *super().describe()]


class Right(Base):
    def describe(self):
        return ["right", *super().describe()]


class Combined(Left, Right):
    def describe(self):
        return ["combined", *super().describe()]


def test_method_lookup_uses_runtime_type():
    value: Base = Combined()

    assert value.describe() == ["combined", "left", "right", "base"]


def test_super_follows_mro_instead_of_naming_one_parent():
    assert Combined.__mro__ == (Combined, Left, Right, Base, object)
    assert Combined().describe() == ["combined", "left", "right", "base"]


def test_explicit_base_call_bypasses_cooperative_dispatch():
    value = Combined()

    assert Base.describe(value) == ["base"]


def test_isinstance_tracks_the_complete_inheritance_graph():
    value = Combined()

    assert isinstance(value, Combined)
    assert isinstance(value, Left)
    assert isinstance(value, Right)
    assert isinstance(value, Base)

