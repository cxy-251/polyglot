"""047｜``deque`` 双端窗口与 ``OrderedDict`` 显式重排示例。

``deque`` 适合两端 O(1) append/pop 和固定长度窗口；它不是支持 slicing、快速中间
随机访问的 list 替代品。单个 append/pop 操作是 thread-safe，但“检查后再操作”仍是
多步业务协议，不能据此假设事务原子性。

现代 ``dict`` 已保证 insertion order。``OrderedDict`` 的主要学习价值是主动移动 key、
两端 pop 和同类对象的 order-sensitive equality。当前文件尚未经过 pytest 验证。
"""

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

import itertools
from collections import OrderedDict
from collections import deque

import pytest


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
