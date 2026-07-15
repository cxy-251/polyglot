"""061｜``functools`` 函数缓存与实例缓存属性。

cache/lru_cache 以可哈希调用参数为 key，并强引用参数和返回值直到淘汰或清空；
它们适合纯函数和可复用结果，不适合时间、随机、副作用或每次都应新建的可变对象。
缓存结构在并发更新下保持一致，但两个并发 miss 仍可能重复执行底层函数。
cached_property 把首次结果写进实例 __dict__，之后普通属性读写会遮蔽 descriptor。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.functools.cache python.functools.unbounded-cache
# polyglot-covers: python.functools.lru_cache python.functools.lru-eviction
# polyglot-covers: python.functools.lru-maxsize-zero python.functools.lru-maxsize-none
# polyglot-covers: python.functools.lru-typed python.functools.lru-keyword-order
# polyglot-covers: python.functools.cache-hashable-arguments python.functools.cache-strong-references
# polyglot-covers: python.functools.cache_info python.functools.cache_parameters
# polyglot-covers: python.functools.cache_clear python.functools.cache-wrapped
# polyglot-covers: python.functools.cache-pure-function python.functools.mutable-result-trap
# polyglot-covers: python.functools.method-cache-self
# polyglot-covers: python.functools.cached_property python.functools.cached-property-dict
# polyglot-covers: python.functools.cached-property-write python.functools.cached-property-delete
# polyglot-covers: python.functools.cached-property-slots python.functools.property-cache-alternative




import gc
from functools import cache, cached_property, lru_cache
import weakref
import pytest
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
from collections import UserDict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from functools import singledispatch, singledispatchmethod

def test_cache_reuses_recursive_results_without_an_eviction_limit():
    """@cache 等价于 lru_cache(maxsize=None)，递归子问题只会真正计算一次。"""

    calls = []

    @cache
    def fibonacci(number):
        calls.append(number)
        if number < 2:
            return number
        return fibonacci(number - 1) + fibonacci(number - 2)

    assert fibonacci(10) == 55
    assert sorted(calls) == list(range(11))

    before = len(calls)
    assert fibonacci(8) == 21
    assert len(calls) == before
    assert fibonacci.cache_parameters() == {"maxsize": None, "typed": False}


def test_lru_cache_records_hits_misses_capacity_and_current_size():
    """cache_info 是 named tuple，可用于判断容量是否匹配真实命中模式。"""

    @lru_cache(maxsize=2)
    def square(number):
        return number * number

    assert square(2) == 4
    assert square(2) == 4
    assert square(3) == 9

    info = square.cache_info()
    assert (info.hits, info.misses, info.maxsize, info.currsize) == (1, 2, 2, 2)


def test_lru_eviction_uses_recent_access_not_insertion_order():
    """命中会把 key 提升为最近使用；容量满后淘汰最久未使用项。"""

    calls = []

    @lru_cache(maxsize=2)
    def identify(value):
        calls.append(value)
        return value

    identify("A")
    identify("B")
    identify("A")
    identify("C")
    identify("A")
    identify("B")

    assert calls == ["A", "B", "C", "B"]
    assert identify.cache_info().hits == 2
    assert identify.cache_info().misses == 4


def test_lru_maxsize_zero_tracks_calls_without_storing_results():
    """maxsize=0 可保留 wrapper/统计接口但禁用存储，每次调用都是 miss。"""

    calls = 0

    @lru_cache(maxsize=0)
    def compute(value):
        nonlocal calls
        calls += 1
        return value * 2

    assert compute(5) == 10
    assert compute(5) == 10
    assert calls == 2
    assert compute.cache_info().currsize == 0
    assert compute.cache_info().misses == 2


def test_lru_maxsize_none_disables_eviction_but_not_memoization():
    """无界缓存只做 dict lookup，适合 key 空间本身有界的纯函数；开放输入会持续增长。"""

    @lru_cache(maxsize=None)
    def identity(value):
        return value

    for value in range(20):
        identity(value)
    for value in range(20):
        identity(value)

    info = identity.cache_info()
    assert (info.hits, info.misses, info.currsize) == (20, 20, 20)


def test_typed_true_separates_equal_immediate_arguments_by_type():
    """bool/int/float 可能数值相等；typed=True 把直接参数类型纳入 cache key。"""

    calls = []

    @lru_cache(maxsize=None, typed=True)
    def describe(value):
        calls.append(type(value).__name__)
        return type(value).__name__

    assert describe(1) == "int"
    assert describe(1.0) == "float"
    assert describe(True) == "bool"
    assert describe(1) == "int"
    assert calls == ["int", "float", "bool"]


def test_keyword_order_can_create_distinct_cache_entries():
    """缓存不承诺规范化 keyword 顺序；语义等价的不同传参顺序可能分别 miss。"""

    @lru_cache(maxsize=None)
    def items(**values):
        return tuple(sorted(values.items()))

    assert items(left=1, right=2) == items(right=2, left=1)
    assert items.cache_info().misses == 2
    assert items.cache_info().hits == 0


def test_cache_arguments_must_be_hashable():
    """cache 底层使用 dict；list/dict 等可变参数不能直接作为 key，应先转 tuple 或稳定标识。"""

    @cache
    def total(values):
        return sum(values)

    with pytest.raises(TypeError, match="unhashable"):
        total([1, 2, 3])
    assert total((1, 2, 3)) == 6


def test_cache_parameters_returns_an_informational_copy():
    """修改 cache_parameters() 的新 dict 不会动态重配现有 wrapper。"""

    @lru_cache(maxsize=4, typed=True)
    def identity(value):
        return value

    parameters = identity.cache_parameters()
    parameters["maxsize"] = 999

    assert identity.cache_parameters() == {"maxsize": 4, "typed": True}


def test_cache_clear_invalidates_entries_and_resets_statistics():
    """清空不仅释放结果，还把 hits/misses/currsize 重置，适合测试隔离或数据版本切换。"""

    @lru_cache(maxsize=2)
    def identity(value):
        return value

    identity(1)
    identity(1)
    assert identity.cache_info().hits == 1

    identity.cache_clear()

    assert identity.cache_info().hits == 0
    assert identity.cache_info().misses == 0
    assert identity.cache_info().currsize == 0


def test_wrapped_attribute_bypasses_cache_for_introspection_or_recomputation():
    """直接调用 __wrapped__ 执行原函数，不查缓存，也不改变 wrapper 的 hit/miss 统计。"""

    calls = 0

    @lru_cache(maxsize=2)
    def compute(value: int) -> int:
        """返回加一后的值。"""

        nonlocal calls
        calls += 1
        return value + 1

    assert compute(4) == 5
    assert compute(4) == 5
    assert compute.__wrapped__(4) == 5

    assert calls == 2
    assert (compute.cache_info().hits, compute.cache_info().misses) == (1, 1)
    assert compute.__name__ == "compute"
    assert compute.__annotations__ == {"value": int, "return": int}


def test_cache_holds_strong_references_until_clear():
    """参数和结果不会因外部引用消失而自动释放；长生命周期服务应限制容量或主动 clear。"""

    class Payload:
        pass

    @cache
    def remember(payload):
        return payload

    payload = Payload()
    reference = weakref.ref(payload)
    remember(payload)

    del payload
    gc.collect()
    assert reference() is not None

    remember.cache_clear()
    gc.collect()
    assert reference() is None


def test_caching_a_mutable_result_reuses_the_same_mutated_object():
    """需要“每次新对象”的 factory 不应缓存；调用者修改返回值会污染所有后续命中。"""

    @cache
    def make_bucket(name):
        return [name]

    first = make_bucket("jobs")
    first.append("mutated")
    second = make_bucket("jobs")

    assert second is first
    assert second == ["jobs", "mutated"]


def test_cached_method_keys_include_self_and_separate_instances():
    """装饰实例方法时 self 是 cache key 的一部分，同参数在不同实例上分别缓存。"""

    class Multiplier:
        def __init__(self, factor):
            self.factor = factor
            self.calls = 0

        @lru_cache(maxsize=None)
        def apply(self, value):
            self.calls += 1
            return self.factor * value

    double = Multiplier(2)
    triple = Multiplier(3)

    assert double.apply(5) == 10
    assert double.apply(5) == 10
    assert triple.apply(5) == 15
    assert (double.calls, triple.calls) == (1, 1)


def test_cached_property_computes_once_then_stores_a_normal_instance_attribute():
    """首次读取调用 descriptor 并写入 __dict__；之后直接由实例 dict 命中。"""

    class Report:
        def __init__(self):
            self.calls = 0

        @cached_property
        def summary(self):
            self.calls += 1
            return {"version": self.calls}

    report = Report()
    first = report.summary
    second = report.summary

    assert first is second
    assert report.calls == 1
    assert report.__dict__["summary"] is first


def test_cached_property_allows_override_and_delete_for_recomputation():
    """普通 assignment 遮蔽 descriptor；del 删除缓存/覆盖值，下一次读取重新执行方法。"""

    class Sequence:
        def __init__(self, values):
            self.values = values
            self.calls = 0

        @cached_property
        def total(self):
            self.calls += 1
            return sum(self.values)

    sequence = Sequence([1, 2])
    assert sequence.total == 3

    sequence.total = 99
    assert sequence.total == 99
    assert sequence.calls == 1

    del sequence.total
    sequence.values.append(3)
    assert sequence.total == 6
    assert sequence.calls == 2


def test_cached_property_without_a_mutable_instance_dict_fails():
    """只定义 __slots__ 且不包含 __dict__ 的实例没有位置保存同名缓存属性。"""

    class Slotted:
        __slots__ = ("value",)

        def __init__(self, value):
            self.value = value

        @cached_property
        def doubled(self):
            return self.value * 2

    with pytest.raises(TypeError, match="__dict__"):
        Slotted(5).doubled


def test_property_over_cache_is_an_alternative_for_hashable_slotted_instances():
    """property 不写实例 dict，内层 cache 以 self 为 key；代价是 cache 会强引用实例。"""

    class Slotted:
        __slots__ = ("value",)

        def __init__(self, value):
            self.value = value

        @property
        @cache
        def doubled(self):
            return self.value * 2

    instance = Slotted(5)

    assert instance.doubled == 10
    assert instance.doubled == 10
    assert Slotted.doubled.fget.cache_info().hits == 1


# ``functools`` 偏函数、归约、比较适配与装饰器元数据。
#
# partial 冻结调用参数但不自动复制 function 元数据；partialmethod 则参与 descriptor
# 绑定并正确插入 self/cls。reduce 明确执行左折叠。wraps/update_wrapper 让装饰器保留
# 名称、文档、注解、自定义属性和 __wrapped__ 链，避免破坏 introspection 与调试工具。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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


# ``functools`` 单分派通用函数与方法。
#
# singledispatch 只按第一个参数的运行时类型选择实现，沿 MRO/ABC 寻找最具体注册，
# 并以 object 注册的原函数作为最终 fallback。singledispatchmethod 跳过 self/cls，
# 按第一个普通参数分派；与 classmethod 等 descriptor 叠加时必须放在最外层。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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
