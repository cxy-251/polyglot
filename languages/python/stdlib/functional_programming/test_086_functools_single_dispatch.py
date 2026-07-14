"""086｜``functools`` 单分派通用函数与方法。

singledispatch 只按第一个参数的运行时类型选择实现，沿 MRO/ABC 寻找最具体注册，
并以 object 注册的原函数作为最终 fallback。singledispatchmethod 跳过 self/cls，
按第一个普通参数分派；与 classmethod 等 descriptor 叠加时必须放在最外层。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.functools.singledispatch python.functools.first-argument-dispatch
# polyglot-covers: python.functools.singledispatch-default python.functools.object-fallback
# polyglot-covers: python.functools.singledispatch-register-annotation
# polyglot-covers: python.functools.singledispatch-register-explicit
# polyglot-covers: python.functools.singledispatch-register-functional
# polyglot-covers: python.functools.singledispatch-register-return
# polyglot-covers: python.functools.singledispatch-mro python.functools.singledispatch-abc
# polyglot-covers: python.functools.singledispatch-dispatch python.functools.singledispatch-registry
# polyglot-covers: python.functools.singledispatch-cache-invalidation
# polyglot-covers: python.functools.singledispatchmethod python.functools.first-non-self-dispatch
# polyglot-covers: python.functools.singledispatchmethod-classmethod
# polyglot-covers: python.functools.singledispatchmethod-staticmethod

from collections import UserDict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from functools import singledispatch, singledispatchmethod

import pytest


def make_renderer():
    """每个测试按需创建独立 registry，避免动态注册跨案例泄漏。"""

    @singledispatch
    def render(value, *, prefix="default"):
        return prefix, "object", repr(value)

    @render.register
    def _(value: int, *, prefix="default"):
        return prefix, "int", str(value)

    @render.register(list)
    def _(value, *, prefix="default"):
        return prefix, "list", ",".join(map(str, value))

    return render


def test_generic_function_uses_registered_type_or_object_fallback():
    """没有更具体注册时执行最初函数；它自动作为 object 实现保存在 registry。"""

    render = make_renderer()

    assert render(42) == ("default", "int", "42")
    assert render([1, 2]) == ("default", "list", "1,2")
    assert render("text") == ("default", "object", "'text'")
    assert object in render.registry


def test_dispatch_uses_only_the_first_argument_type():
    """后续参数与 keyword 只传给选中的实现，不参与 overload resolution。"""

    @singledispatch
    def describe(first, second):
        return "default", type(second).__name__

    @describe.register(int)
    def _(first, second):
        return "int", type(second).__name__

    assert describe(1, "text") == ("int", "str")
    assert describe("1", 99) == ("default", "int")


def test_annotation_registration_infers_the_first_parameter_type():
    """@generic.register 不带参数时从实现的首参数 annotation 推断注册 class。"""

    render = make_renderer()

    assert render.dispatch(int) is render.registry[int]
    assert render(7)[1] == "int"


def test_explicit_registration_supports_unannotated_implementations():
    """@register(complex) 适合旧函数或不希望把运行时类型写进 annotation 的实现。"""

    render = make_renderer()

    @render.register(complex)
    def render_complex(value, *, prefix="default"):
        return prefix, "complex", (value.real, value.imag)

    assert render(1 + 2j) == ("default", "complex", (1.0, 2.0))


def test_functional_registration_accepts_a_preexisting_callable():
    """generic.register(type, function) 不要求 decorator 语法，便于插件式注册已有函数。"""

    render = make_renderer()

    def render_none(value, *, prefix="default"):
        assert value is None
        return prefix, "none", "null"

    returned = render.register(type(None), render_none)

    assert returned is render_none
    assert render(None) == ("default", "none", "null")


def test_register_decorator_returns_the_undecorated_variant():
    """返回实现本身而非 generic wrapper，因而能独立单测、叠加注册或 pickle。"""

    render = make_renderer()

    @render.register(float)
    @render.register(Decimal)
    def render_number(value, *, prefix="default"):
        return prefix, "number", str(value)

    assert render_number is not render
    assert render_number(1.5) == ("default", "number", "1.5")
    assert render(1.5)[1] == "number"
    assert render(Decimal("2.5"))[1] == "number"


def test_mro_selects_the_most_specific_registered_base_class():
    """bool 是 int subclass；两者都有实现时选择 bool，删除不了注册时可新建 generic 比较 fallback。"""

    render = make_renderer()

    @render.register(bool)
    def _(value, *, prefix="default"):
        return prefix, "bool", str(value)

    assert render(True)[1] == "bool"
    assert render(1)[1] == "int"

    int_only = make_renderer()
    assert int_only(True)[1] == "int"


def test_abstract_base_class_registration_covers_concrete_implementations():
    """注册 Mapping 后 dict/UserDict 都沿 ABC 关系命中，无需逐个 concrete class 注册。"""

    render = make_renderer()

    @render.register(Mapping)
    def _(value, *, prefix="default"):
        return prefix, "mapping", tuple(value.items())

    assert render({"a": 1})[1] == "mapping"
    assert render(UserDict({"b": 2}))[1] == "mapping"


def test_more_specific_concrete_registration_beats_an_abc_registration():
    """list 同时是 Sequence；exact/MRO 更具体实现优先于较宽的 ABC 实现。"""

    render = make_renderer()

    @render.register(Sequence)
    def _(value, *, prefix="default"):
        return prefix, "sequence", len(value)

    assert render([1, 2])[1] == "list"
    assert render((1, 2))[1] == "sequence"
    assert render("ab")[1] == "sequence"


def test_dispatch_reports_the_implementation_for_a_type_without_calling_it():
    """dispatch(cls) 适合 introspection、诊断插件覆盖或直接独立调用选中实现。"""

    render = make_renderer()
    int_implementation = render.dispatch(int)
    fallback = render.dispatch(str)

    assert int_implementation(9) == ("default", "int", "9")
    assert fallback("x") == ("default", "object", "'x'")
    assert fallback is render.registry[object]


def test_registry_is_a_read_only_mapping_of_explicit_registrations():
    """registry 可枚举但不能直接赋值；新增/替换实现必须走 register 以清理 dispatch cache。"""

    render = make_renderer()

    assert set(render.registry) == {object, int, list}
    with pytest.raises(TypeError):
        render.registry[str] = lambda value: value


def test_new_registration_invalidates_a_previous_dispatch_decision():
    """某类型先走 fallback 后再 register，后续调用必须立即命中新实现而非旧 dispatch cache。"""

    render = make_renderer()
    assert render("before")[1] == "object"

    @render.register(str)
    def _(value, *, prefix="default"):
        return prefix, "str", value.upper()

    assert render("after") == ("default", "str", "AFTER")


def test_register_rejects_a_nonclass_explicit_dispatch_key():
    """3.10 的单分派注册键必须是 class/ABC，不能传实例或任意值。"""

    render = make_renderer()

    with pytest.raises(TypeError):
        render.register(42, lambda value: value)


class Negator:
    @singledispatchmethod
    def negate(self, value):
        raise TypeError(f"不支持 {type(value).__name__}")

    @negate.register
    def _(self, value: int):
        return -value

    @negate.register
    def _(self, value: bool):
        return not value


def test_singledispatchmethod_skips_self_and_uses_first_normal_argument():
    """两个实例共享 method registry，但选择依据是 value 类型而不是 self 类型。"""

    negator = Negator()

    assert negator.negate(5) == -5
    assert negator.negate(True) is False
    with pytest.raises(TypeError, match="str"):
        negator.negate("text")


def test_singledispatchmethod_can_be_extended_after_class_creation():
    """descriptor 暴露 register，可在插件加载时添加新类型实现。"""

    class Formatter:
        @singledispatchmethod
        def format(self, value):
            return f"default:{value}"

    @Formatter.format.register(float)
    def _(self, value):
        return f"float:{value:.2f}"

    assert Formatter().format(1.5) == "float:1.50"
    assert Formatter().format("x") == "default:x"


def test_singledispatchmethod_must_wrap_classmethod_to_keep_register_visible():
    """singledispatchmethod 放最外层，内部 classmethod 先完成 cls 绑定，再按 value 分派。"""

    class Converter:
        @singledispatchmethod
        @classmethod
        def convert(cls, value):
            return cls.__name__, "default", value

        @convert.register
        @classmethod
        def _(cls, value: int):
            return cls.__name__, "int", str(value)

    assert Converter.convert(3) == ("Converter", "int", "3")
    assert Converter().convert("x") == ("Converter", "default", "x")


def test_singledispatchmethod_delegates_to_staticmethod_descriptor():
    """staticmethod 没有 self/cls；第一个参数本身就是分派目标，外层仍需保留 register。"""

    class Parser:
        @singledispatchmethod
        @staticmethod
        def parse(value):
            return "default", value

        @parse.register
        @staticmethod
        def _(value: bytes):
            return "bytes", value.decode("ascii")

    assert Parser.parse(b"abc") == ("bytes", "abc")
    assert Parser().parse("abc") == ("default", "abc")
