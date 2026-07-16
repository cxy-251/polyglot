"""045｜``Counter`` 有符号计数与 ``defaultdict`` 缺失值工厂示例。

两者都是 ``dict`` 子类，却专门化了不同协议：``Counter.__missing__`` 对读取返回 0
但不插入；``defaultdict.__missing__`` 会调用无参 factory、插入并返回新值。理解这个
副作用差异比记住几个便利方法更重要。

Counter 的普通变更 API 可保留零/负 count，multiset 数学运算只输出正 count。本文
锁定 Python 3.10 的 ``total()`` 和 rich comparison 语义。
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
import itertools
from collections import OrderedDict
from collections import deque
import subprocess
import sys
from collections import ChainMap
from collections import namedtuple

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


# ``deque`` 双端窗口与 ``OrderedDict`` 显式重排示例。
#
# ``deque`` 适合两端 O(1) append/pop 和固定长度窗口；它不是支持 slicing、快速中间
# 随机访问的 list 替代品。单个 append/pop 操作是 thread-safe，但“检查后再操作”仍是
# 多步业务协议，不能据此假设事务原子性。
#
# 现代 ``dict`` 已保证 insertion order。``OrderedDict`` 的主要学习价值是主动移动 key、
# 两端 pop 和同类对象的 order-sensitive equality。

# polyglot-covers: python.collections.deque python.deque.construction
# polyglot-covers: python.deque.append-pop python.deque.extend
# polyglot-covers: python.deque.bounded python.deque.maxlen python.deque.eviction
# polyglot-covers: python.deque.rotate python.deque.reverse
# polyglot-covers: python.deque.copy python.deque.search-remove
# polyglot-covers: python.deque.indexing python.deque.no-slicing
# polyglot-covers: python.deque.sequence-operators python.deque.error-boundaries
# polyglot-covers: python.deque.tail python.deque.moving-window
# polyglot-covers: python.deque.round-robin python.deque.thread-safety-boundary
# polyglot-covers: python.collections.OrderedDict python.ordereddict.order
# polyglot-covers: python.ordereddict.move_to_end python.ordereddict.popitem
# polyglot-covers: python.ordereddict.reverse-iteration python.ordereddict.equality
# polyglot-covers: python.ordereddict.merge python.ordereddict.lru




def test_deque_constructs_left_to_right_and_exposes_read_only_maxlen():
    """iterable 按 append 顺序装入；未指定 maxlen 时可无限增长。"""

    queue = deque(["first", "second", "third"])
    bounded = deque([1, 2, 3, 4], maxlen=3)

    assert list(queue) == ["first", "second", "third"]
    assert queue.maxlen is None
    assert list(bounded) == [2, 3, 4]
    assert bounded.maxlen == 3

    with pytest.raises(AttributeError):
        bounded.maxlen = 10
    with pytest.raises(ValueError):
        deque(maxlen=-1)


def test_append_and_pop_work_from_both_ends():
    """右端可作 stack，左取右入可作 FIFO queue，无需 list.pop(0) 搬移元素。"""

    tasks = deque(["compile"])

    assert tasks.append("test") is None
    assert tasks.appendleft("fetch") is None
    assert list(tasks) == ["fetch", "compile", "test"]

    assert tasks.popleft() == "fetch"
    assert tasks.pop() == "test"
    assert list(tasks) == ["compile"]


def test_extend_preserves_order_but_extendleft_reverses_input_order():
    """extendleft 等价于连续 appendleft；最后读到的输入最终位于最左侧。"""

    values = deque([3])

    assert values.extend([4, 5]) is None
    assert list(values) == [3, 4, 5]

    assert values.extendleft([2, 1, 0]) is None
    assert list(values) == [0, 1, 2, 3, 4, 5]


def test_bounded_append_evicts_from_the_opposite_end():
    """满载时右加淘汰最左旧值，左加淘汰最右值，适合 recent-history。"""

    recent = deque([1, 2, 3], maxlen=3)

    recent.append(4)
    assert list(recent) == [2, 3, 4]

    recent.appendleft(1)
    assert list(recent) == [1, 2, 3]

    recent.extend([4, 5])
    assert list(recent) == [3, 4, 5]


def test_zero_length_deque_consumes_input_but_stores_nothing():
    """maxlen=0 仍遍历 iterable；不要把它误当成完全不执行数据源。"""

    consumed = []

    def source():
        for value in range(3):
            consumed.append(value)
            yield value

    sink = deque(source(), maxlen=0)
    sink.append(99)

    assert consumed == [0, 1, 2]
    assert list(sink) == []
    assert sink.maxlen == 0


def test_insert_into_full_bounded_deque_raises_instead_of_evicting():
    """insert 需要保留所有既有相对位置；满载时与 append 的淘汰语义不同。"""

    bounded = deque(["a", "b", "c"], maxlen=3)

    with pytest.raises(IndexError):
        bounded.insert(1, "new")

    assert list(bounded) == ["a", "b", "c"]


def test_rotate_uses_positive_right_and_negative_left_steps_modulo_length():
    """rotate 不创建新 deque；超过长度的步数会循环折算。"""

    values = deque([1, 2, 3, 4, 5])

    assert values.rotate(2) is None
    assert list(values) == [4, 5, 1, 2, 3]

    values.rotate(-1)
    assert list(values) == [5, 1, 2, 3, 4]

    values.rotate(11)  # 11 % 5 == 1，向右一步。
    assert list(values) == [4, 5, 1, 2, 3]


def test_reverse_copy_and_reversed_have_distinct_mutation_semantics():
    """reverse 原地修改；reversed 延迟迭代；copy 浅复制容器并保留 maxlen。"""

    shared = ["payload"]
    values = deque([shared, ["other"]], maxlen=4)
    copied = values.copy()

    assert isinstance(copied, deque)
    assert copied.maxlen == 4
    assert copied is not values
    assert copied[0] is shared
    assert list(reversed(values)) == [["other"], ["payload"]]

    assert values.reverse() is None
    assert list(values) == [["other"], ["payload"]]
    assert list(copied) == [["payload"], ["other"]]


def test_count_index_remove_and_clear_follow_sequence_conventions():
    """index 的 stop 为半开边界；remove 只删除首个相等元素。"""

    values = deque(["a", "b", "a", "c", "a"])

    assert values.count("a") == 3
    assert values.index("a") == 0
    assert values.index("a", 1, 4) == 2
    assert values.remove("a") is None
    assert list(values) == ["b", "a", "c", "a"]

    assert values.clear() is None
    assert list(values) == []


def test_deque_supports_integer_indexing_but_not_slicing():
    """两端索引快，中间索引会逐段走访；需要切片/大量随机访问时使用 list。"""

    values = deque([10, 20, 30, 40])

    assert values[0] == 10
    assert values[-1] == 40
    assert values[2] == 30
    values[1] = 200
    assert list(values) == [10, 200, 30, 40]

    with pytest.raises(TypeError):
        _ = values[1:3]
    with pytest.raises(TypeError):
        values[1:3] = [2, 3]


def test_deque_addition_and_multiplication_preserve_deque_sequence_behavior():
    """组合运算返回 deque；左 operand 的 maxlen 也约束拼接后的右侧窗口。"""

    left = deque([1, 2])
    right = deque([3, 4])

    assert left + right == deque([1, 2, 3, 4])
    assert left * 2 == deque([1, 2, 1, 2])
    assert 2 * left == deque([1, 2, 1, 2])
    assert left == deque([1, 2])

    bounded = deque([1, 2], maxlen=3)
    combined = bounded + deque([3, 4])
    assert combined == deque([2, 3, 4], maxlen=3)
    assert combined.maxlen == 3

    bounded *= 2
    assert bounded == deque([2, 1, 2], maxlen=3)


def test_deque_empty_and_missing_element_operations_raise_specific_errors():
    """pop 使用 IndexError，搜索/删除缺失值使用 ValueError。"""

    empty = deque()

    with pytest.raises(IndexError):
        empty.pop()
    with pytest.raises(IndexError):
        empty.popleft()
    with pytest.raises(ValueError):
        deque([1, 2]).index(3)
    with pytest.raises(ValueError):
        deque([1, 2]).remove(3)


def test_bounded_deque_is_a_direct_tail_and_recent_history_recipe():
    """maxlen 自动丢弃旧值，避免手工写 if len(...) > n: popleft()。"""

    events = ["connect", "authenticate", "query", "commit", "disconnect"]
    recent_three = deque(events, maxlen=3)

    assert list(recent_three) == ["query", "commit", "disconnect"]

    recent_three.append("reconnect")
    assert list(recent_three) == ["commit", "disconnect", "reconnect"]


def test_deque_supports_a_fixed_size_moving_average_recipe():
    """popleft 与 append 同时推进窗口，sum 只增减离开/进入的元素。"""

    def moving_average(iterable, window_size):
        iterator = iter(iterable)
        window = deque(itertools.islice(iterator, window_size - 1))
        window.appendleft(0)
        running_total = sum(window)

        for value in iterator:
            running_total += value - window.popleft()
            window.append(value)
            yield running_total / window_size

    readings = [40, 30, 50, 46, 39, 44]

    assert list(moving_average(readings, 3)) == [40.0, 42.0, 45.0, 43.0]


def test_deque_rotation_builds_a_deterministic_round_robin_recipe():
    """当前 iterator 未耗尽就 rotate 到队尾；耗尽时 popleft 移出调度队列。"""

    def round_robin(*iterables):
        pending = deque(map(iter, iterables))
        while pending:
            iterator = pending[0]
            try:
                yield next(iterator)
            except StopIteration:
                pending.popleft()
            else:
                pending.rotate(-1)

    assert list(round_robin("ABC", "D", "EF")) == ["A", "D", "E", "B", "F", "C"]

    # append/pop 单操作的 thread-safe 保证不等于上述多步调度循环是原子事务。


def test_ordereddict_overwrite_keeps_position_until_explicitly_moved():
    """给已有 key 赋新值只改 value；最近更新顺序需要 move_to_end 或 subclass。"""

    settings = OrderedDict([("theme", "light"), ("language", "zh")])
    settings["theme"] = "dark"
    settings["timezone"] = "UTC"

    assert list(settings.items()) == [
        ("theme", "dark"),
        ("language", "zh"),
        ("timezone", "UTC"),
    ]


def test_move_to_end_moves_an_existing_key_to_either_side():
    """last=False 的左移没有同样直接的普通 dict 方法。"""

    order = OrderedDict.fromkeys("abcde")

    assert order.move_to_end("b") is None
    assert "".join(order) == "acdeb"

    order.move_to_end("b", last=False)
    assert "".join(order) == "bacde"

    with pytest.raises(KeyError):
        order.move_to_end("missing")


def test_popitem_selects_lifo_or_fifo_end_explicitly():
    """last=True 从右侧 LIFO，last=False 从左侧 FIFO。"""

    queue = OrderedDict([("first", 1), ("second", 2), ("third", 3)])

    assert queue.popitem(last=False) == ("first", 1)
    assert queue.popitem(last=True) == ("third", 3)
    assert list(queue.items()) == [("second", 2)]

    queue.popitem()
    with pytest.raises(KeyError):
        queue.popitem(last=False)


def test_ordereddict_and_its_views_support_reverse_iteration():
    """keys/items/values view 都能 reversed，而不必先 materialize 后再反转。"""

    order = OrderedDict([("a", 1), ("b", 2), ("c", 3)])

    assert list(reversed(order)) == ["c", "b", "a"]
    assert list(reversed(order.keys())) == ["c", "b", "a"]
    assert list(reversed(order.items())) == [("c", 3), ("b", 2), ("a", 1)]
    assert list(reversed(order.values())) == [3, 2, 1]


def test_ordereddict_equality_is_order_sensitive_only_against_same_type():
    """同类比较包含顺序；作为普通 Mapping 的替代品时与 dict 比较只看键值。"""

    first = OrderedDict([("a", 1), ("b", 2)])
    reversed_order = OrderedDict([("b", 2), ("a", 1)])

    assert first != reversed_order
    assert first == {"b": 2, "a": 1}
    assert reversed_order == {"a": 1, "b": 2}


def test_ordereddict_merge_preserves_type_existing_positions_and_new_key_order():
    """覆盖 key 留在原位，右侧新 key 按遇到顺序追加。"""

    original = OrderedDict([("a", 1), ("b", 2)])
    merged = original | {"b": 20, "c": 3, "d": 4}

    assert isinstance(merged, OrderedDict)
    assert list(merged.items()) == [("a", 1), ("b", 20), ("c", 3), ("d", 4)]
    assert list(original.items()) == [("a", 1), ("b", 2)]

    original |= {"b": 200, "e": 5}
    assert list(original.items()) == [("a", 1), ("b", 200), ("e", 5)]


def test_last_updated_order_subclass_moves_overwritten_keys_to_the_end():
    """覆盖 __setitem__ 后复用 move_to_end，可把 insertion order 改为 update order。"""

    class LastUpdatedOrderedDict(OrderedDict):
        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            self.move_to_end(key)

    values = LastUpdatedOrderedDict()
    values["a"] = 1
    values["b"] = 2
    values["a"] = 10

    assert list(values.items()) == [("b", 2), ("a", 10)]


def test_ordereddict_supports_a_small_deterministic_lru_cache():
    """命中时移到末尾，超容量时从左侧 FIFO 淘汰最久未使用项。"""

    class LRUCache:
        def __init__(self, capacity):
            self.capacity = capacity
            self.data = OrderedDict()

        def get(self, key):
            value = self.data[key]
            self.data.move_to_end(key)
            return value

        def put(self, key, value):
            self.data[key] = value
            self.data.move_to_end(key)
            if len(self.data) > self.capacity:
                return self.data.popitem(last=False)
            return None

    cache = LRUCache(capacity=2)
    assert cache.put("a", 1) is None
    assert cache.put("b", 2) is None
    assert cache.get("a") == 1

    evicted = cache.put("c", 3)

    assert evicted == ("b", 2)
    assert list(cache.data.items()) == [("a", 1), ("c", 3)]
    with pytest.raises(KeyError):
        cache.get("b")


# ``ChainMap`` 多层映射视图与 ``namedtuple`` 轻量记录示例。
#
# ``ChainMap`` 保留底层 mapping 引用，查询跨层、默认写入只到第一层；它不是合并后的
# dict 副本。``namedtuple`` 则生成真正的 tuple subclass，用字段名补充位置协议而不为
# 每个实例增加 ``__dict__``。
#
# 动态生成类的 pickle 依赖 ``module + typename`` 能在模块 globals 中重新找到同一类。
# 该边界在子进程验证，避免依赖 pytest 的测试模块导入名。

# polyglot-covers: python.collections.ChainMap python.chainmap.maps
# polyglot-covers: python.chainmap.lookup-precedence python.chainmap.first-map-writes
# polyglot-covers: python.chainmap.reference-view python.chainmap.iteration-order
# polyglot-covers: python.chainmap.new_child python.chainmap.parents
# polyglot-covers: python.chainmap.flatten-snapshot python.chainmap.merge
# polyglot-covers: python.chainmap.configuration-layers python.chainmap.deep-write
# polyglot-covers: python.collections.namedtuple python.namedtuple.factory
# polyglot-covers: python.namedtuple.tuple-protocol python.namedtuple.immutability
# polyglot-covers: python.namedtuple._make python.namedtuple._asdict
# polyglot-covers: python.namedtuple._replace python.namedtuple._fields
# polyglot-covers: python.namedtuple.defaults python.namedtuple.rename
# polyglot-covers: python.namedtuple.module-pickle python.namedtuple.subclass




def test_empty_chainmap_still_contains_one_writable_mapping():
    """无参数时不会得到无层对象；自动创建的 root dict 可直接接收写入。"""

    scope = ChainMap()

    assert scope.maps == [{}]
    assert len(scope.maps) == 1

    scope["name"] = "root"
    assert scope.maps[0] == {"name": "root"}


def test_chainmap_lookup_uses_front_to_back_precedence():
    """命令行覆盖环境，环境覆盖默认值；未遮蔽 key 继续向后查找。"""

    command_line = {"color": "blue"}
    environment = {"user": "alice", "color": "green"}
    defaults = {"user": "guest", "color": "red", "debug": False}
    settings = ChainMap(command_line, environment, defaults)

    assert settings["color"] == "blue"
    assert settings["user"] == "alice"
    assert settings["debug"] is False
    assert "debug" in settings
    assert settings.maps == [command_line, environment, defaults]


def test_underlying_mapping_changes_are_visible_because_chainmap_keeps_references():
    """ChainMap 是 live view；外部更新不会像预先 dict.update 的 snapshot 那样隔离。"""

    local = {}
    defaults = {"timeout": 30}
    settings = ChainMap(local, defaults)

    defaults["timeout"] = 60
    defaults["retries"] = 3

    assert settings["timeout"] == 60
    assert settings["retries"] == 3

    local["timeout"] = 5
    assert settings["timeout"] == 5


def test_assignment_update_and_missing_setdefault_write_only_the_first_map():
    """查到父层不意味着写回父层；所有新赋值集中在最前 scope。"""

    local = {}
    parent = {"color": "red"}
    settings = ChainMap(local, parent)

    settings["color"] = "blue"
    settings.update(timeout=10)
    inserted = settings.setdefault("retries", 3)

    assert inserted == 3
    assert local == {"color": "blue", "timeout": 10, "retries": 3}
    assert parent == {"color": "red"}

    # 已在父层找到时，setdefault 返回现有值，不额外制造遮蔽 entry。
    second = ChainMap({}, {"language": "zh"})
    assert second.setdefault("language", "en") == "zh"
    assert second.maps[0] == {}


def test_delete_and_pop_do_not_reach_into_parent_maps():
    """默认 mutation 边界是第一层；父层同名 key 不会被深删。"""

    local = {"temporary": 1}
    parent = {"persistent": 2}
    settings = ChainMap(local, parent)

    del settings["temporary"]
    assert "temporary" not in local

    with pytest.raises(KeyError):
        del settings["persistent"]
    with pytest.raises(KeyError):
        settings.pop("persistent")

    assert parent == {"persistent": 2}
    assert settings["persistent"] == 2


def test_iteration_order_matches_updates_from_last_map_to_first_map():
    """lookup 从前向后，但 key iteration 模拟先复制最后层、再逐层 update。"""

    baseline = {"music": "bach", "art": "rembrandt"}
    adjustments = {"art": "van gogh", "opera": "carmen"}
    combined = ChainMap(adjustments, baseline)

    assert list(combined) == ["music", "art", "opera"]
    assert list(combined.items()) == [
        ("music", "bach"),
        ("art", "van gogh"),
        ("opera", "carmen"),
    ]

    expected = baseline.copy()
    expected.update(adjustments)
    assert dict(combined) == expected


def test_new_child_creates_an_independent_front_scope_over_shared_parents():
    """child 写入自己的 local map，查询仍复用 parent 的底层 mapping 引用。"""

    root = ChainMap({"name": "root", "theme": "light"})
    child = root.new_child()

    assert child.maps[1:] == root.maps
    assert child.maps[0] == {}
    assert child["theme"] == "light"

    child["theme"] = "dark"
    child["local_only"] = True

    assert child["theme"] == "dark"
    assert root["theme"] == "light"
    assert "local_only" not in root


def test_new_child_accepts_explicit_map_and_python_310_keyword_initializers():
    """3.10 kwargs 会更新传入的新 front map；该 mapping 仍按引用暴露。"""

    root = ChainMap({"root": True})
    local = {"request_id": "abc"}
    child = root.new_child(local, debug=True, retries=2)

    assert child.maps[0] is local
    assert local == {"request_id": "abc", "debug": True, "retries": 2}
    assert child["root"] is True

    keyword_only_child = root.new_child(user="ada")
    assert keyword_only_child.maps[0] == {"user": "ada"}


def test_parents_skips_the_first_scope_without_copying_remaining_maps():
    """parents 类似 nonlocal view；新 ChainMap 复用原链的第二层及以后。"""

    local = {"value": "local"}
    enclosing = {"value": "enclosing", "shared": 1}
    global_scope = {"value": "global", "fallback": 2}
    scope = ChainMap(local, enclosing, global_scope)
    parents = scope.parents

    assert parents.maps == [enclosing, global_scope]
    assert parents.maps[0] is enclosing
    assert parents["value"] == "enclosing"

    enclosing["shared"] = 10
    assert parents["shared"] == 10


def test_public_maps_list_can_reorder_lookup_precedence_explicitly():
    """maps 是唯一状态且可修改；调用方也因此要自行维护至少一层等不变量。"""

    first = {"mode": "first"}
    second = {"mode": "second"}
    scope = ChainMap(first, second)

    assert scope["mode"] == "first"

    scope.maps.reverse()
    assert scope["mode"] == "second"
    assert scope.maps == [second, first]


def test_flattening_to_dict_creates_a_snapshot_instead_of_a_live_view():
    """dict(chain) 固化当时的有效键值；后续底层变化只反映在 ChainMap。"""

    overrides = {"color": "blue"}
    defaults = {"color": "red", "size": "medium"}
    view = ChainMap(overrides, defaults)
    snapshot = dict(view)

    overrides["color"] = "green"
    defaults["size"] = "large"
    defaults["new"] = True

    assert view["color"] == "green"
    assert view["size"] == "large"
    assert view["new"] is True
    assert snapshot == {"color": "blue", "size": "medium"}


def test_chainmap_merge_returns_a_new_chain_and_inplace_merge_updates_front():
    """``|`` copy 第一层后更新，父 mappings 继续共享；``|=`` 直接写当前第一层。"""

    local = {"color": "blue"}
    defaults = {"color": "red", "size": "medium"}
    settings = ChainMap(local, defaults)
    merged = settings | {"color": "green", "debug": True}

    assert isinstance(merged, ChainMap)
    assert merged["color"] == "green"
    assert merged["debug"] is True
    assert settings["color"] == "blue"
    assert "debug" not in settings
    assert merged.maps[0] is not local
    assert merged.maps[1] is defaults

    settings |= {"color": "purple", "timeout": 5}
    assert local == {"color": "purple", "timeout": 5}
    assert settings["size"] == "medium"


def test_configuration_precedence_ignores_unspecified_command_line_values():
    """先过滤 None，避免“未提供的 CLI 值”错误遮蔽环境和默认配置。"""

    parsed_arguments = {"user": None, "color": "blue"}
    command_line = {
        key: value
        for key, value in parsed_arguments.items()
        if value is not None
    }
    environment = {"user": "from-env"}
    defaults = {"user": "guest", "color": "red", "debug": False}
    settings = ChainMap(command_line, environment, defaults)

    assert dict(settings) == {
        "user": "from-env",
        "color": "blue",
        "debug": False,
    }


def test_deep_chainmap_subclass_can_route_updates_to_the_first_existing_layer():
    """需要 deep-write 时必须显式改协议；新 key 仍放第一层。"""

    class DeepChainMap(ChainMap):
        def __setitem__(self, key, value):
            for mapping in self.maps:
                if key in mapping:
                    mapping[key] = value
                    return
            self.maps[0][key] = value

        def __delitem__(self, key):
            for mapping in self.maps:
                if key in mapping:
                    del mapping[key]
                    return
            raise KeyError(key)

    local = {"local": 1}
    parent = {"shared": 2, "remove": 3}
    scope = DeepChainMap(local, parent)

    scope["shared"] = 20
    scope["new"] = 4
    del scope["remove"]

    assert local == {"local": 1, "new": 4}
    assert parent == {"shared": 20}

    with pytest.raises(KeyError):
        del scope["missing"]


def test_namedtuple_accepts_string_or_iterable_fields_and_is_a_tuple_subclass():
    """字段串可用空白/逗号分隔；实例仍完整实现 tuple 位置协议。"""

    Point = namedtuple("Point", "x, y")
    Color = namedtuple("Color", ["red", "green", "blue"])
    point = Point(11, y=22)
    color = Color(128, 255, 0)

    assert issubclass(Point, tuple)
    assert isinstance(point, tuple)
    assert point == (11, 22)
    assert point[0] == point.x == 11
    assert point[1] == point.y == 22
    assert tuple(point) == (11, 22)
    assert color.green == 255

    x, y = point
    assert (x, y) == (11, 22)
    assert {point: "coordinate"}[Point(11, 22)] == "coordinate"


def test_namedtuple_repr_fields_and_instances_are_immutable_and_slot_based():
    """repr 用 name=value；字段和 tuple item 均不可赋值，实例没有 __dict__。"""

    Point = namedtuple("Point", "x y")
    point = Point(3, 4)

    assert repr(point) == "Point(x=3, y=4)"
    assert Point._fields == ("x", "y")
    assert not hasattr(point, "__dict__")

    with pytest.raises(AttributeError):
        point.x = 10
    with pytest.raises(TypeError):
        point[0] = 10


def test_make_constructs_from_iterable_and_validates_exact_arity():
    """_make 适合 CSV/数据库 row；字段数不匹配不会静默截断或补齐。"""

    Point = namedtuple("Point", "x y")

    assert Point._make(iter([5, 6])) == Point(5, 6)

    with pytest.raises(TypeError):
        Point._make([5])
    with pytest.raises(TypeError):
        Point._make([5, 6, 7])


def test_asdict_returns_a_regular_ordered_dict_in_python_310():
    """3.8+ _asdict 返回普通 dict；语言层 insertion order 已保存字段顺序。"""

    Point = namedtuple("Point", "x y")
    mapping = Point(7, 8)._asdict()

    assert type(mapping) is dict
    assert mapping == {"x": 7, "y": 8}
    assert list(mapping) == ["x", "y"]


def test_replace_returns_a_new_record_and_rejects_unknown_fields():
    """_replace 不修改原 tuple；Python 3.10 对未知字段抛 ValueError。"""

    Account = namedtuple("Account", "owner balance")
    original = Account("Ada", 10)
    updated = original._replace(balance=25)

    assert original == Account("Ada", 10)
    assert updated == Account("Ada", 25)
    assert updated is not original

    with pytest.raises(ValueError):
        original._replace(currency="USD")


def test_fields_can_compose_larger_record_types():
    """_fields 是稳定 introspection tuple，可复用而不手抄字段名。"""

    Point = namedtuple("Point", "x y")
    Color = namedtuple("Color", "red green blue")
    Pixel = namedtuple("Pixel", Point._fields + Color._fields)

    pixel = Pixel(11, 22, 128, 255, 0)

    assert Pixel._fields == ("x", "y", "red", "green", "blue")
    assert pixel.x == 11
    assert pixel.blue == 0


def test_defaults_apply_only_to_rightmost_fields_and_are_introspectable():
    """defaults 与函数 positional defaults 一样从最右字段对齐。"""

    Account = namedtuple(
        "Account",
        "kind balance currency",
        defaults=[0, "USD"],
    )

    assert Account._field_defaults == {"balance": 0, "currency": "USD"}
    assert Account("premium") == Account("premium", 0, "USD")
    assert Account("premium", 100) == Account("premium", 100, "USD")

    with pytest.raises(TypeError):
        Account()


def test_rename_replaces_keywords_duplicates_and_leading_underscore_fields():
    """rename=False 严格失败；rename=True 用 _位置 生成可用且唯一的字段。"""

    invalid_fields = ["class", "value", "value", "_hidden"]

    with pytest.raises(ValueError):
        namedtuple("Invalid", invalid_fields)

    Renamed = namedtuple("Renamed", invalid_fields, rename=True)
    value = Renamed(1, 2, 3, 4)

    assert Renamed._fields == ("_0", "value", "_2", "_3")
    assert (value._0, value.value, value._2, value._3) == (1, 2, 3, 4)


def test_module_parameter_and_global_typename_binding_control_pickle_lookup():
    """pickle 按 module.typename 找类；只改 __module__ 而没有同名全局绑定仍不够。"""

    program = r'''
import pickle
from collections import namedtuple

Record = namedtuple("Record", "identifier", module=__name__)
value = Record(7)
restored = pickle.loads(pickle.dumps(value))
assert restored == value
assert type(restored) is Record

Unbound = namedtuple("OtherRecord", "identifier", module=__name__)
try:
    pickle.dumps(Unbound(8))
except pickle.PicklingError:
    pass
else:
    raise AssertionError("OtherRecord is not bound in module globals")

print("isolated-namedtuple-pickle-ok")
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "isolated-namedtuple-pickle-ok"


def test_namedtuple_subclass_adds_computed_behavior_without_instance_dict():
    """subclass 设 __slots__=() 可增加 property/docstring，同时维持 tuple 存储模型。"""

    PointBase = namedtuple("PointBase", "x y")

    class Point(PointBase):
        __slots__ = ()

        @property
        def squared_distance(self):
            return self.x ** 2 + self.y ** 2

    Point.__doc__ = "二维不可变坐标"
    Point.x.__doc__ = "横坐标"
    point = Point(3, 4)

    assert point.squared_distance == 25
    assert Point.__doc__ == "二维不可变坐标"
    assert Point.x.__doc__ == "横坐标"
    assert not hasattr(point, "__dict__")
