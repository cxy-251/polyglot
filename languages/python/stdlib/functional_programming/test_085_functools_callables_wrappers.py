"""085｜``functools`` 偏函数、归约、比较适配与装饰器元数据。

partial 冻结调用参数但不自动复制 function 元数据；partialmethod 则参与 descriptor
绑定并正确插入 self/cls。reduce 明确执行左折叠。wraps/update_wrapper 让装饰器保留
名称、文档、注解、自定义属性和 __wrapped__ 链，避免破坏 introspection 与调试工具。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.functools.partial python.functools.partial-argument-order
# polyglot-covers: python.functools.partial-keyword-override python.functools.partial-attributes
# polyglot-covers: python.functools.partial-class-static python.functools.partial-metadata
# polyglot-covers: python.functools.partialmethod python.functools.partialmethod-descriptor
# polyglot-covers: python.functools.reduce python.functools.reduce-left-fold
# polyglot-covers: python.functools.reduce-initializer python.functools.reduce-empty
# polyglot-covers: python.functools.cmp_to_key python.functools.comparator-adapter
# polyglot-covers: python.functools.total_ordering python.functools.rich-comparison-generation
# polyglot-covers: python.functools.total-ordering-notimplemented python.functools.total-ordering-inherited
# polyglot-covers: python.functools.wraps python.functools.update_wrapper
# polyglot-covers: python.functools.WRAPPER_ASSIGNMENTS python.functools.WRAPPER_UPDATES
# polyglot-covers: python.functools.wrapper-metadata python.functools.__wrapped__

from functools import (
    WRAPPER_ASSIGNMENTS,
    WRAPPER_UPDATES,
    cmp_to_key,
    partial,
    partialmethod,
    reduce,
    total_ordering,
    update_wrapper,
    wraps,
)
from inspect import signature
from operator import add

import pytest


def test_partial_prepends_frozen_positional_arguments():
    """调用 partial 时的新 positional 参数追加在 frozen args 后面。"""

    def render(prefix, value, suffix):
        return f"{prefix}{value}{suffix}"

    bracketed = partial(render, "[")

    assert bracketed("content", "]") == "[content]"


def test_partial_call_keywords_extend_and_override_frozen_keywords():
    """新 keyword 与冻结值合并，同名项以调用时提供的值为准。"""

    def connect(host, *, port=80, secure=False):
        return host, port, secure

    production = partial(connect, "example.test", port=443, secure=True)

    assert production() == ("example.test", 443, True)
    assert production(port=8443) == ("example.test", 8443, True)
    assert production(secure=False) == ("example.test", 443, False)


def test_partial_exposes_read_only_func_args_and_keywords_attributes():
    """三个属性引用不可重新赋值，便于 introspection；keywords 指向的 dict 内容仍可修改。"""

    def greet(greeting, name, *, punctuation):
        return f"{greeting}, {name}{punctuation}"

    hello = partial(greet, "Hello", punctuation="!")

    assert hello.func is greet
    assert hello.args == ("Hello",)
    assert hello.keywords == {"punctuation": "!"}

    hello.keywords["punctuation"] = "."
    assert hello("Ada") == "Hello, Ada."

    with pytest.raises(AttributeError):
        hello.func = str
    with pytest.raises(AttributeError):
        hello.args = ()
    with pytest.raises(AttributeError):
        hello.keywords = {}


def test_partial_does_not_automatically_copy_function_name_or_docstring():
    """partial 是 callable object 而非普通 function；需要展示名称时应由调用者显式赋属性。"""

    def parse_binary(text):
        """解析二进制文本。"""

        return int(text, base=2)

    parser = partial(parse_binary)

    assert not hasattr(parser, "__name__")
    assert parser.__doc__ != parse_binary.__doc__

    parser.__name__ = "binary_parser"
    assert parser.__name__ == "binary_parser"


def test_partial_stored_on_a_class_does_not_bind_the_instance():
    """partial 没有 function descriptor 的自动绑定；作为类属性访问时表现得像 staticmethod。"""

    class Parser:
        binary = partial(int, base=2)

    assert Parser.binary("101") == 5
    assert Parser().binary("101") == 5


def test_partialmethod_binds_self_before_frozen_arguments():
    """partialmethod 专门用于方法定义；底层普通函数先绑定 self，再追加冻结的 state。"""

    class Cell:
        def __init__(self):
            self.alive = False

        def set_state(self, state):
            self.alive = bool(state)

        set_alive = partialmethod(set_state, True)
        set_dead = partialmethod(set_state, False)

    cell = Cell()
    cell.set_alive()
    assert cell.alive is True
    cell.set_dead()
    assert cell.alive is False


def test_partialmethod_delegates_to_a_classmethod_descriptor():
    """底层是 classmethod 等 descriptor 时，partialmethod 会先委托其 __get__ 完成 cls 绑定。"""

    class Formatter:
        @classmethod
        def describe(cls, prefix, value):
            return cls.__name__, prefix, value

        tagged = partialmethod(describe, "tag")

    assert Formatter.tagged(3) == ("Formatter", "tag", 3)
    assert Formatter().tagged(4) == ("Formatter", "tag", 4)


def test_reduce_is_a_left_associative_fold():
    """非结合运算最能看出顺序：10-3-2 按 ((10-3)-2) 得 5。"""

    steps = []

    def subtract(accumulator, value):
        steps.append((accumulator, value))
        return accumulator - value

    assert reduce(subtract, [10, 3, 2]) == 5
    assert steps == [(10, 3), (7, 2)]


def test_reduce_initializer_is_logically_placed_before_all_items():
    """initializer 不是空输入专用 fallback；非空时也会先作为 accumulator 参与第一步。"""

    assert reduce(add, [1, 2, 3], 100) == 106
    assert reduce(lambda path, name: f"{path}/{name}", ["a", "b"], "root") == "root/a/b"


def test_reduce_empty_and_singleton_inputs_have_distinct_contracts():
    """空 iterable 只有提供 initializer 才有结果；单元素且无 initializer 时直接返回该元素。"""

    calls = []

    def combine(left, right):
        calls.append((left, right))
        return left + right

    assert reduce(combine, [42]) == 42
    assert calls == []
    assert reduce(combine, [], "identity") == "identity"

    with pytest.raises(TypeError):
        reduce(combine, [])


def test_cmp_to_key_adapts_negative_zero_positive_comparison_results():
    """旧式 comparator 比较两个值；adapter 产生一元 key object 供现代 sorted/key API 使用。"""

    def by_length_then_text(left, right):
        if len(left) != len(right):
            return len(left) - len(right)
        return (left > right) - (left < right)

    words = ["pear", "a", "fig", "kiwi", "bee"]

    assert sorted(words, key=cmp_to_key(by_length_then_text)) == ["a", "bee", "fig", "kiwi", "pear"]


def test_cmp_to_key_zero_preserves_stable_input_order():
    """comparator 返回 0 表示排序等价；Python 稳定排序保留这些元素的原相对顺序。"""

    def compare_first_letter(left, right):
        return (left[0] > right[0]) - (left[0] < right[0])

    words = ["beta", "apple", "boat", "apricot"]

    assert sorted(words, key=cmp_to_key(compare_first_letter)) == ["apple", "apricot", "beta", "boat"]


@total_ordering
class Version:
    """最小 total_ordering 示例，只提供 eq 与 lt。"""

    def __init__(self, major, minor):
        self.parts = (major, minor)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.parts < other.parts


def test_total_ordering_derives_remaining_rich_comparisons():
    """由 __eq__ 与一个 ordering 方法可生成 <=、>、>=，但性能热点可手写全部六个方法。"""

    old = Version(3, 9)
    current = Version(3, 10)
    same = Version(3, 10)

    assert old < current
    assert old <= current
    assert current > old
    assert current >= old
    assert current == same
    assert current <= same
    assert current >= same


def test_total_ordering_preserves_notimplemented_for_unknown_types():
    """底层比较返回 NotImplemented 后允许 reflected fallback；双方都不支持时才由运算符报错。"""

    version = Version(3, 10)

    assert (version == (3, 10)) is False
    with pytest.raises(TypeError):
        version < (3, 10)
    with pytest.raises(TypeError):
        version >= (3, 10)


def test_total_ordering_requires_at_least_one_ordering_method():
    """只定义相等还不足以推导方向，decorator 在创建 class 时立即拒绝。"""

    with pytest.raises(ValueError):
        @total_ordering
        class EqualityOnly:
            def __eq__(self, other):
                return isinstance(other, EqualityOnly)


def test_total_ordering_does_not_override_an_inherited_comparison_method():
    """superclass 已声明的方法会保留，即使它与 subclass 新定义的比较策略不协调。"""

    class Base:
        def __gt__(self, other):
            return "inherited"

    @total_ordering
    class Child(Base):
        def __eq__(self, other):
            return self is other

        def __lt__(self, other):
            return False

    assert Child().__gt__(Child()) == "inherited"


def test_wraps_preserves_metadata_custom_attributes_and_original_access():
    """默认 assigned 复制标准 metadata，updated 合并 function.__dict__，并设置 __wrapped__。"""

    def trace(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper

    def original(value: int) -> str:
        """把整数转成文本。"""

        return str(value)

    original.category = "conversion"
    decorated = trace(original)

    assert decorated(5) == "5"
    assert decorated.__name__ == "original"
    assert decorated.__doc__ == "把整数转成文本。"
    assert decorated.__annotations__ == {"value": int, "return": str}
    assert decorated.category == "conversion"
    assert decorated.__wrapped__ is original
    assert signature(decorated) == signature(original)


def test_without_wraps_a_decorator_exposes_wrapper_metadata():
    """调用逻辑仍正确，但名称、文档和签名会描述内部 wrapper，影响帮助和 introspection。"""

    def decorate(function):
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper

    def original(value):
        """original documentation"""

        return value

    decorated = decorate(original)

    assert decorated(1) == 1
    assert decorated.__name__ == "wrapper"
    assert decorated.__doc__ is None
    assert not hasattr(decorated, "__wrapped__")


def test_update_wrapper_can_customize_assigned_and_updated_attribute_sets():
    """assigned 做替换，updated 做 mapping.update；即使列表为空也总会设置 __wrapped__。"""

    def original():
        """original doc"""

    original.label = "source"

    def wrapper():
        return original()

    result = update_wrapper(wrapper, original, assigned=("__name__",), updated=())

    assert result is wrapper
    assert wrapper.__name__ == "original"
    assert wrapper.__doc__ is None
    assert not hasattr(wrapper, "label")
    assert wrapper.__wrapped__ is original


def test_wrapper_attribute_constants_document_the_default_policy():
    """constants 可复用于自定义 decorator 工具，不必复制版本相关的默认 attribute 名单。"""

    assert "__name__" in WRAPPER_ASSIGNMENTS
    assert "__doc__" in WRAPPER_ASSIGNMENTS
    assert "__annotations__" in WRAPPER_ASSIGNMENTS
    assert WRAPPER_UPDATES == ("__dict__",)
