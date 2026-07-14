"""046｜``Counter`` 有符号计数与 ``defaultdict`` 缺失值工厂示例。

两者都是 ``dict`` 子类，却专门化了不同协议：``Counter.__missing__`` 对读取返回 0
但不插入；``defaultdict.__missing__`` 会调用无参 factory、插入并返回新值。理解这个
副作用差异比记住几个便利方法更重要。

Counter 的普通变更 API 可保留零/负 count，multiset 数学运算只输出正 count。本文
锁定 Python 3.10 的 ``total()`` 和 rich comparison 语义。当前文件尚未经过 pytest
验证。
"""

# polyglot-covers: python.stdlib.collections python.collections.Counter
# polyglot-covers: python.counter.construction python.counter.missing-zero
# polyglot-covers: python.counter.elements python.counter.most_common
# polyglot-covers: python.counter.update python.counter.subtract python.counter.total
# polyglot-covers: python.counter.multiset-operators python.counter.unary-operators
# polyglot-covers: python.counter.rich-comparison python.counter.order
# polyglot-covers: python.counter.noninteger-counts python.counter.fromkeys
# polyglot-covers: python.collections.defaultdict python.defaultdict.default_factory
# polyglot-covers: python.defaultdict.__missing__ python.defaultdict.getitem-side-effect
# polyglot-covers: python.defaultdict.grouping python.defaultdict.counting
# polyglot-covers: python.defaultdict.factory-errors python.defaultdict.mutable-sharing
# polyglot-covers: python.defaultdict.copy-merge python.defaultdict.dict-conversion

from collections import Counter
from collections import defaultdict
from fractions import Fraction

import pytest


def test_counter_constructs_from_iterable_mapping_keywords_and_empty_input():
    """iterable 逐元素计数；mapping/keywords 把给定值直接作为初始 count。"""

    from_events = Counter(["login", "logout", "login"])
    from_mapping = Counter({"login": 5, "logout": 2})
    from_keywords = Counter(login=3, timeout=1)

    assert from_events == Counter(login=2, logout=1)
    assert from_mapping["login"] == 5
    assert from_keywords == {"login": 3, "timeout": 1}
    assert Counter() == {}
    assert isinstance(from_events, dict)


def test_counter_missing_read_returns_zero_without_inserting_the_key():
    """Counter 的 __missing__ 是无副作用读取，不像 defaultdict 自动建 entry。"""

    inventory = Counter(apples=3)

    assert inventory["pears"] == 0
    assert "pears" not in inventory
    assert list(inventory) == ["apples"]


def test_zero_count_remains_an_entry_until_explicitly_deleted():
    """count 值与 key 是否存在是两件事；清理零项可 del 或使用 unary plus。"""

    inventory = Counter(apples=1)
    inventory["apples"] -= 1

    assert inventory["apples"] == 0
    assert "apples" in inventory
    assert dict(inventory) == {"apples": 0}

    del inventory["apples"]
    assert "apples" not in inventory
    assert inventory["apples"] == 0


def test_most_common_uses_first_encounter_order_to_break_count_ties():
    """Python 3.7+ Counter 保留 insertion order；同 count 不做字母排序。"""

    requests = Counter(["beta", "alpha", "beta", "alpha", "gamma"])

    assert requests.most_common(2) == [("beta", 2), ("alpha", 2)]
    assert requests.most_common() == [
        ("beta", 2),
        ("alpha", 2),
        ("gamma", 1),
    ]
    assert requests.most_common(None) == requests.most_common()


def test_elements_repeats_only_positive_integer_counts_in_insertion_order():
    """0 和负 count 被忽略；elements 返回迭代器而不是预先展开的大列表。"""

    inventory = Counter()
    inventory["pear"] = 2
    inventory["apple"] = 1
    inventory["sold-out"] = 0
    inventory["backorder"] = -2

    elements = inventory.elements()

    assert iter(elements) is elements
    assert list(elements) == ["pear", "pear", "apple"]


def test_counter_update_adds_counts_instead_of_replacing_like_dict_update():
    """iterable 逐元素 +1，mapping 按 value 累加；两种路径都不是覆盖赋值。"""

    inventory = Counter(apples=2)

    assert inventory.update(["apples", "pears"]) is None
    assert inventory == Counter(apples=3, pears=1)

    inventory.update({"pears": 3, "plums": 2})
    assert inventory == Counter(apples=3, pears=4, plums=2)

    # iterable 中的二元 tuple 会被当作一个 hashable 元素，不会自动解释成 pair。
    pair_counter = Counter()
    pair_counter.update([("apples", 10)])
    assert pair_counter == Counter({("apples", 10): 1})


def test_subtract_and_total_preserve_signed_counts():
    """subtract 原地保留零/负库存；Python 3.10 total 计算代数和而非只加正数。"""

    inventory = Counter(apples=4, pears=2, plums=0)

    assert inventory.subtract({"apples": 1, "pears": 2, "plums": 3}) is None
    inventory.subtract(["apples", "bananas"])

    assert inventory == Counter(apples=2, pears=0, plums=-3, bananas=-1)
    assert inventory.total() == -2
    assert "pears" in inventory
    assert "plums" in inventory


def test_multiset_operators_keep_only_positive_output_counts():
    """加法/正差/交集/并集分别用 sum、difference、min、max，再滤掉非正项。"""

    warehouse = Counter(apples=3, pears=1, stale=-1)
    delivery = Counter(apples=1, pears=2, plums=4)

    assert warehouse + delivery == Counter(apples=4, pears=3, plums=4)
    assert warehouse - delivery == Counter(apples=2)
    assert warehouse & delivery == Counter(apples=1, pears=1)
    assert warehouse | delivery == Counter(apples=3, pears=2, plums=4)

    assert "stale" not in warehouse + delivery
    assert "plums" not in warehouse - delivery


def test_unary_counter_operations_normalize_signed_counts_to_multisets():
    """unary + 取原 counter 的正项；unary - 取负项的绝对值。"""

    balance = Counter(credit=3, settled=0, debt=-4)

    assert +balance == Counter(credit=3)
    assert -balance == Counter(debt=4)
    assert balance == Counter(credit=3, settled=0, debt=-4)


def test_python_310_counter_comparisons_treat_missing_counts_as_zero():
    """3.10 起 equality/subset/superset 比较覆盖所有 key，缺失项视作 0。"""

    minimal = Counter(apples=1)
    explicit_zero = Counter(apples=1, pears=0)
    larger = Counter(apples=2, pears=1)

    assert minimal == explicit_zero
    assert minimal <= explicit_zero
    assert not minimal < explicit_zero
    assert minimal < larger
    assert larger > minimal
    assert larger >= explicit_zero

    # 有符号 count 也参与逐 key 比较；缺失值仍是 0。
    assert Counter(debt=-1) < Counter()


def test_counter_math_order_comes_from_left_then_new_right_keys():
    """数学结果先沿用左 operand 首次出现顺序，再追加右侧才出现的正项。"""

    left = Counter()
    left["beta"] = 1
    left["alpha"] = 1
    right = Counter()
    right["alpha"] = 1
    right["gamma"] = 1
    right["beta"] = 1
    right["delta"] = 1

    combined = left + right

    assert list(combined) == ["beta", "alpha", "gamma", "delta"]
    assert combined == Counter(beta=2, alpha=2, gamma=1, delta=1)


def test_counter_accepts_fractional_counts_but_elements_requires_integers():
    """Counter 本身不强制 int；不同方法只要求完成其自身所需的协议。"""

    weights = Counter(apples=Fraction(3, 2), pears=Fraction(1, 2))
    weights.update({"apples": Fraction(1, 2)})

    assert weights["apples"] == 2
    assert weights.total() == Fraction(5, 2)
    assert weights.most_common(1) == [("apples", Fraction(2, 1))]

    with pytest.raises(TypeError):
        list(weights.elements())


def test_counter_fromkeys_is_intentionally_not_implemented():
    """fromkeys 无法表达“每个 key 初始 count 是什么”，应传 mapping 或 Counter。"""

    with pytest.raises(NotImplementedError):
        Counter.fromkeys(["apples", "pears"])


def test_defaultdict_getitem_calls_zero_argument_factory_and_inserts_once():
    """每个新 key 调一次 factory；已有 key 直接返回同一保存值。"""

    created_values = []

    def make_bucket():
        bucket = []
        created_values.append(bucket)
        return bucket

    grouped = defaultdict(make_bucket)

    first = grouped["fruit"]
    assert first is grouped["fruit"]
    second = grouped["vegetable"]

    assert len(created_values) == 2
    assert first is created_values[0]
    assert second is created_values[1]
    assert first is not second
    assert list(grouped) == ["fruit", "vegetable"]


def test_defaultdict_get_membership_and_setdefault_do_not_share_factory_semantics():
    """只有 __getitem__ 调 __missing__；get/in 不插入，setdefault 使用显式默认值。"""

    calls = []

    def factory():
        calls.append("factory-called")
        return []

    grouped = defaultdict(factory)

    assert grouped.get("missing") is None
    assert grouped.get("missing", ["fallback"]) == ["fallback"]
    assert "missing" not in grouped
    assert calls == []

    explicit = grouped.setdefault("missing", ["seed"])
    assert explicit == ["seed"]
    assert grouped["missing"] is explicit
    assert calls == []


def test_defaultdict_list_set_and_int_factories_support_common_workflows():
    """每个内置类型都被无参调用：list/set 造新容器，int 提供起始 0。"""

    records = [
        ("fruit", "apple"),
        ("fruit", "pear"),
        ("fruit", "apple"),
        ("vegetable", "carrot"),
    ]
    lists = defaultdict(list)
    sets = defaultdict(set)
    counts = defaultdict(int)

    for category, item in records:
        lists[category].append(item)
        sets[category].add(item)
        counts[category] += 1

    assert dict(lists) == {
        "fruit": ["apple", "pear", "apple"],
        "vegetable": ["carrot"],
    }
    assert dict(sets) == {
        "fruit": {"apple", "pear"},
        "vegetable": {"carrot"},
    }
    assert dict(counts) == {"fruit": 3, "vegetable": 1}


def test_constant_factory_can_supply_an_immutable_placeholder():
    """闭包保存配置值，factory 本身仍保持无参调用签名。"""

    def constant_factory(value):
        return lambda: value

    template_values = defaultdict(
        constant_factory("<missing>"),
        name="Ada",
        action="compiled",
    )

    assert "%(name)s %(action)s %(object)s" % template_values == (
        "Ada compiled <missing>"
    )
    assert template_values["object"] == "<missing>"
    assert "object" in template_values


def test_none_factory_restores_normal_dict_keyerror_behavior():
    """defaultdict() 默认 factory=None；此时 __missing__ 以原 key 抛 KeyError。"""

    values = defaultdict()

    assert values.default_factory is None
    with pytest.raises(KeyError) as caught:
        values["missing"]

    assert caught.value.args == ("missing",)
    assert "missing" not in values


def test_factory_exception_propagates_unchanged_and_does_not_insert():
    """工厂失败不是一个默认值；defaultdict 不包装异常也不保存半成品。"""

    class ConfigurationError(Exception):
        pass

    failure = ConfigurationError("bucket configuration missing")

    def broken_factory():
        raise failure

    values = defaultdict(broken_factory)

    with pytest.raises(ConfigurationError) as caught:
        values["jobs"]

    assert caught.value is failure
    assert "jobs" not in values


def test_factory_is_called_without_the_missing_key_argument():
    """default_factory 不是 dict.__missing__(key) callback；需要 key 时应自定义 mapping。"""

    def needs_key(key):
        return [key]

    grouped = defaultdict(needs_key)

    with pytest.raises(TypeError):
        grouped["fruit"]

    assert "fruit" not in grouped


def test_replacing_default_factory_changes_only_future_missing_keys():
    """default_factory 是可写属性；已有值保留原类型，后续 miss 使用新 factory。"""

    values = defaultdict(list)
    values["before"].append("item")

    values.default_factory = set
    values["after"].add("item")

    assert values["before"] == ["item"]
    assert values["after"] == {"item"}

    values.default_factory = None
    with pytest.raises(KeyError):
        values["disabled"]


def test_mutable_factory_must_create_a_fresh_object_for_each_key():
    """返回共享 list 的 factory 会让不相关 key 别名到同一容器。"""

    shared_bucket = []
    unsafe = defaultdict(lambda: shared_bucket)

    unsafe["fruit"].append("apple")

    assert unsafe["vegetable"] is unsafe["fruit"]
    assert unsafe["vegetable"] == ["apple"]

    safe = defaultdict(list)
    safe["fruit"].append("apple")
    assert safe["vegetable"] == []
    assert safe["vegetable"] is not safe["fruit"]


def test_defaultdict_copy_merge_repr_and_plain_dict_conversion():
    """copy/left merge 保留 factory；dict() 只复制 items，主动丢弃 missing 行为。"""

    original = defaultdict(list, fruit=["apple"])
    shallow = original.copy()
    merged = original | {"vegetable": ["carrot"]}

    assert isinstance(shallow, defaultdict)
    assert shallow.default_factory is list
    assert shallow["fruit"] is original["fruit"]

    assert isinstance(merged, defaultdict)
    assert merged.default_factory is list
    assert dict(merged) == {
        "fruit": ["apple"],
        "vegetable": ["carrot"],
    }
    assert "defaultdict" in repr(merged)
    assert "list" in repr(merged)

    plain = dict(original)
    assert type(plain) is dict
    with pytest.raises(KeyError):
        plain["missing"]

    original |= {"grain": ["rice"]}
    assert original.default_factory is list
    assert original["grain"] == ["rice"]
