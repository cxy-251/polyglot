"""024｜``dict`` 的键契约、插入顺序、动态视图与合并工作流示例。

dict 把 hashable key 映射到任意 value，并保证迭代遵循插入顺序。键是否相同由
equality/hash 契约共同决定；keys/items/values 则是跟随原字典变化的动态视图，
不是创建时刻的列表快照。

通用 equality/hash 协议和 dict display/comprehension 已在 002、014、017 展示；
本文件聚焦内置映射类型自身。内容基于 Python 3.10 Mapping Types、Dictionary
View Objects 和 PEP 584；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.type.dict python.builtin.dict python.literal.dict
# polyglot-covers: python.dict.key-contract python.dict.insertion-order
# polyglot-covers: python.dict.get python.dict.setdefault python.dict.__missing__
# polyglot-covers: python.dict.update python.dict.merge-operators
# polyglot-covers: python.dict.keys python.dict.values python.dict.items
# polyglot-covers: python.dict.view.mapping python.dict.reverse-iteration
# polyglot-covers: python.dict.pop python.dict.popitem python.dict.clear
# polyglot-covers: python.dict.copy python.dict.fromkeys
# polyglot-covers: python.dict.iteration-mutation

import pytest


def test_dict_constructs_from_literals_mappings_pairs_and_keywords():
    """构造器可合并 mapping/键值 iterable 与关键字，后提供的值覆盖前者。"""

    literal = {"host": "localhost", "port": 8000}
    pairs = dict([("host", "localhost"), ("port", 8000)])
    keywords = dict(host="localhost", port=8000)
    overridden = dict(literal, port=9000, debug=True)

    assert literal == pairs == keywords
    assert overridden == {
        "host": "localhost",
        "port": 9000,
        "debug": True,
    }
    assert dict(zip(["a", "b"], [1, 2])) == {"a": 1, "b": 2}
    assert {name: len(name) for name in ["go", "python"]} == {
        "go": 2,
        "python": 6,
    }


def test_duplicate_or_reassigned_key_keeps_position_but_uses_latest_value():
    """覆盖已有键不会重新插入该键；删除后再添加才会移动到末尾。"""

    settings = {"first": 1, "second": 2, "first": 10}

    assert settings == {"first": 10, "second": 2}
    assert list(settings) == ["first", "second"]

    settings["first"] = 11
    assert list(settings) == ["first", "second"]

    del settings["first"]
    settings["first"] = 12
    assert list(settings) == ["second", "first"]


def test_keys_must_be_hashable_and_equal_numeric_keys_collide():
    """可变容器不能作键；相等且 hash 相同的数值键代表同一条目。"""

    mapping = {True: "bool", 1: "int", 1.0: "float"}

    assert len(mapping) == 1
    assert mapping[True] == mapping[1] == mapping[1.0] == "float"

    with pytest.raises(TypeError):
        {[]: "list key"}

    with pytest.raises(TypeError):
        {("tuple", []): "tuple contains unhashable list"}

    # bool/int 的详细关系见 019。需要保留来源类型时用 `(type_tag, value)` 复合键。


def test_equal_hashes_alone_do_not_make_unequal_objects_the_same_key():
    """dict 会先按 hash 定位候选，再用 equality 区分真正的键。"""

    class CollidingKey:
        def __init__(self, name):
            self.name = name

        def __hash__(self):
            return 42

        def __eq__(self, other):
            return isinstance(other, CollidingKey) and self.name == other.name

    first = CollidingKey("first")
    second = CollidingKey("second")
    mapping = {first: 1, second: 2}

    assert len(mapping) == 2
    assert mapping[CollidingKey("first")] == 1
    assert mapping[CollidingKey("second")] == 2

    # hash 碰撞只影响查找候选和性能，不等于键相等。


def test_mutating_state_used_by_hash_breaks_future_key_lookup():
    """键进入 dict 后，参与 equality/hash 的状态必须保持不变。"""

    class BadMutableKey:
        def __init__(self, value):
            self.value = value

        def __hash__(self):
            return hash(self.value)

        def __eq__(self, other):
            return isinstance(other, BadMutableKey) and self.value == other.value

    key = BadMutableKey(1)
    mapping = {key: "stored"}
    assert mapping[key] == "stored"

    key.value = 2

    assert key not in mapping
    assert list(mapping.keys())[0] is key

    # 条目没有消失；对象的新 hash 把查询带到另一个桶。实际键类型应不可变，或只用
    # 不变字段实现 hash/equality。


def test_subscription_get_and_sentinel_distinguish_missing_from_stored_none():
    """get 的默认 None 会与显式存储的 None 混在一起，sentinel 可保留区别。"""

    mapping = {"present": None}
    missing = object()

    assert mapping.get("present") is None
    assert mapping.get("absent") is None
    assert mapping.get("present", missing) is None
    assert mapping.get("absent", missing) is missing

    with pytest.raises(KeyError):
        mapping["absent"]


def test_dict_subclass_missing_hook_only_handles_subscription():
    """``__missing__`` 由 dict.__getitem__ 调用，get/contains 等方法不调用它。"""

    class Labels(dict):
        def __missing__(self, key):
            return f"<{key}>"

    labels = Labels(known="value")

    assert labels["known"] == "value"
    assert labels["unknown"] == "<unknown>"
    assert labels.get("unknown") is None
    assert "unknown" not in labels
    assert list(labels) == ["known"]

    # 返回缺失值不会自动写回字典；需要缓存时应在 __missing__ 内显式赋值。


def test_setdefault_supports_grouping_but_default_expression_is_eager():
    """setdefault 缺失时插入默认值，存在时返回旧值；实参仍会在调用前求值。"""

    grouped = {}
    for category, item in [("fruit", "pear"), ("fruit", "apple"), ("veg", "pea")]:
        grouped.setdefault(category, []).append(item)

    assert grouped == {
        "fruit": ["pear", "apple"],
        "veg": ["pea"],
    }

    calls = []

    def make_default():
        calls.append("built")
        return ["unused"]

    returned = grouped.setdefault("fruit", make_default())

    assert calls == ["built"]
    assert returned is grouped["fruit"]
    assert "unused" not in returned

    # 默认值昂贵或有副作用时，先判断 key、使用 __missing__，或使用 defaultdict。


def test_assignment_update_and_merge_have_clear_overwrite_direction():
    """update 原地修改并返回 None；同名键以最后提供的右侧值为准。"""

    settings = {"host": "localhost", "port": 8000}
    settings["debug"] = False
    returned = settings.update({"port": 9000}, debug=True)

    assert returned is None
    assert settings == {
        "host": "localhost",
        "port": 9000,
        "debug": True,
    }


def test_merge_operators_distinguish_new_result_from_in_place_update():
    """``left | right`` 创建普通 dict，``|=`` 修改左侧，冲突都由右侧获胜。"""

    defaults = {"host": "localhost", "port": 8000}
    overrides = {"port": 9000, "debug": True}

    merged = defaults | overrides

    assert merged == {"host": "localhost", "port": 9000, "debug": True}
    assert list(merged) == ["host", "port", "debug"]
    assert defaults == {"host": "localhost", "port": 8000}

    defaults |= overrides
    assert defaults == merged

    # 被覆盖的 port 保留左侧原位置；右侧新键 debug 追加到末尾。


def test_keys_values_and_items_are_dynamic_views_not_snapshots():
    """创建 view 后对原字典的后续修改会立即反映在 view 中。"""

    mapping = {"a": 1, "b": 2}
    keys = mapping.keys()
    values = mapping.values()
    items = mapping.items()

    mapping["c"] = 3
    mapping["a"] = 10

    assert list(keys) == ["a", "b", "c"]
    assert list(values) == [10, 2, 3]
    assert list(items) == [("a", 10), ("b", 2), ("c", 3)]

    snapshot = list(items)
    mapping["d"] = 4
    assert ("d", 4) in items
    assert ("d", 4) not in snapshot


def test_keys_and_hashable_items_support_set_like_operations():
    """keys 总是 set-like；items 在键值对可 hash 时也能参与集合运算。"""

    mapping = {"a": 1, "b": 2, "c": 3}

    assert mapping.keys() & {"b", "x"} == {"b"}
    assert mapping.keys() - {"a", "c"} == {"b"}
    assert mapping.items() & {("b", 2), ("x", 9)} == {("b", 2)}

    unhashable_values = {"a": []}
    with pytest.raises(TypeError):
        set(unhashable_values.items())


def test_dict_view_mapping_property_is_a_live_read_only_proxy_in_python_310():
    """视图的 mapping 属性暴露原字典的只读动态代理。"""

    original = {"a": 1}
    proxy = original.keys().mapping

    assert proxy["a"] == 1
    original["b"] = 2
    assert proxy == {"a": 1, "b": 2}

    with pytest.raises(TypeError):
        proxy["c"] = 3

    # 只读限制的是通过 proxy 写入；它不是冻结快照，原字典变化仍然可见。


def test_iteration_and_reversed_follow_insertion_order():
    """dict、keys、values 和 items 都可按插入顺序正向或反向遍历。"""

    mapping = {"first": 1, "second": 2, "third": 3}

    assert list(mapping) == ["first", "second", "third"]
    assert list(reversed(mapping)) == ["third", "second", "first"]
    assert list(reversed(mapping.keys())) == ["third", "second", "first"]
    assert list(reversed(mapping.values())) == [3, 2, 1]
    assert list(reversed(mapping.items())) == [
        ("third", 3),
        ("second", 2),
        ("first", 1),
    ]


def test_dict_equality_ignores_insertion_order_while_iteration_preserves_it():
    """mapping equality 比较键值关系，不比较条目的历史顺序。"""

    left = {"a": 1, "b": 2}
    right = {"b": 2, "a": 1}

    assert left == right
    assert list(left) == ["a", "b"]
    assert list(right) == ["b", "a"]


def test_pop_popitem_del_and_clear_expose_different_deletion_results():
    """pop 按键返回值，popitem 按 LIFO 返回键值对，del 不返回被删值。"""

    mapping = {"a": 1, "b": 2, "c": 3}

    assert mapping.pop("b") == 2
    assert mapping.pop("missing", 99) == 99
    assert mapping.popitem() == ("c", 3)

    del mapping["a"]
    assert mapping == {}

    with pytest.raises(KeyError):
        mapping.pop("missing")

    with pytest.raises(KeyError):
        mapping.popitem()

    mapping.update(a=1, b=2)
    assert mapping.clear() is None
    assert mapping == {}


def test_dict_copy_and_constructor_make_only_shallow_copies():
    """外层映射独立，嵌套 value 仍与原字典共享。"""

    original = {"items": [1], "meta": {"ready": False}}
    copied = original.copy()
    reconstructed = dict(original)

    assert copied is not original and reconstructed is not original
    assert copied["items"] is original["items"]
    assert reconstructed["meta"] is original["meta"]

    copied["items"].append(2)
    copied["new"] = "outer only"

    assert original["items"] == [1, 2]
    assert "new" not in original


def test_fromkeys_reuses_one_mutable_default_for_every_key():
    """fromkeys 的 value 只求值一次；它不会为每个键调用工厂。"""

    shared = dict.fromkeys(["a", "b"], [])
    shared["a"].append(1)

    assert shared == {"a": [1], "b": [1]}
    assert shared["a"] is shared["b"]

    independent = {key: [] for key in ["a", "b"]}
    independent["a"].append(1)

    assert independent == {"a": [1], "b": []}


def test_changing_dict_size_during_iteration_raises_runtime_error():
    """迭代器依赖结构版本；遍历时增删键会使其失效。"""

    mapping = {"keep": 1, "remove": 0, "also_keep": 2}

    with pytest.raises(RuntimeError, match="changed size during iteration"):
        for key in mapping:
            if mapping[key] == 0:
                del mapping[key]

    assert "remove" not in mapping

    # 异常发生前删除已经生效，操作不是事务。实际代码应先计算修改集合。


def test_snapshot_or_comprehension_supports_safe_structural_rewrite():
    """遍历键快照可原地删键；推导式适合产生清晰的新映射。"""

    in_place = {"keep": 1, "remove": 0, "also_keep": 2}
    for key in list(in_place):
        if in_place[key] == 0:
            del in_place[key]

    rebuilt = {
        key: value
        for key, value in {"keep": 1, "remove": 0, "also_keep": 2}.items()
        if value != 0
    }

    expected = {"keep": 1, "also_keep": 2}
    assert in_place == expected
    assert rebuilt == expected


def test_updating_existing_values_during_iteration_does_not_change_size():
    """只替换已有 value 不改变键集合，因此允许在键迭代中进行。"""

    counters = {"a": 1, "b": 2}

    for key in counters:
        counters[key] += 10

    assert counters == {"a": 11, "b": 12}

    # 若更新逻辑可能新增缺失键，仍应改用快照，避免未来代码变化引入结构修改。
