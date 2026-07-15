"""048｜``Mapping`` 与 key/item/value live view 的只读协议示例。

Mapping 只要求 lookup、key iteration 和 length 三个 primitive。默认 mixin 用它们实现
``get``、membership、equality 与三种 view；view 保存底层 mapping 引用，不是 list
快照。Key/item view 继承 Set，而 value view 允许重复，只是普通 Collection。

本文件同时区分 ABC 默认 view 和 Python 3.10 内置 dict view 的额外能力。当前文件
尚未经过 pytest 验证。
"""

# polyglot-covers: python.collections.abc.Mapping python.mapping.abstract-primitives
# polyglot-covers: python.mapping.key-iteration python.mapping.get
# polyglot-covers: python.mapping.contains python.mapping.keyerror-boundary
# polyglot-covers: python.mapping.equality python.mapping.reversed-boundary
# polyglot-covers: python.collections.abc.MappingView python.mapping-view.repr
# polyglot-covers: python.collections.abc.KeysView python.keys-view.set-operations
# polyglot-covers: python.collections.abc.ItemsView python.items-view.membership
# polyglot-covers: python.items-view.unhashable-values python.items-view.identity-equality
# polyglot-covers: python.collections.abc.ValuesView python.values-view.duplicates
# polyglot-covers: python.mapping-view.live-reference python.mapping-view.iteration-mutation
# polyglot-covers: python.dict-view.registrations python.dict-view.mapping-proxy
# polyglot-covers: python.types.MappingProxyType python.mapping.generic-alias




from collections.abc import Collection
from collections.abc import ItemsView
from collections.abc import KeysView
from collections.abc import Mapping
from collections.abc import MappingView
from collections.abc import Reversible
from collections.abc import Set
from collections.abc import ValuesView
from types import GenericAlias
from types import MappingProxyType
import pytest
from collections.abc import MutableMapping

class ReadOnlyMap(Mapping):
    """以 insertion-ordered dict 存储的最小 Mapping，并记录 lookup。"""

    def __init__(self, values=()):
        self.storage = dict(values)
        self.lookups = []

    def __getitem__(self, key):
        self.lookups.append(key)
        return self.storage[key]

    def __iter__(self):
        return iter(self.storage)

    def __len__(self):
        return len(self.storage)

    def __repr__(self):
        return f"ReadOnlyMap({self.storage!r})"


def test_mapping_requires_getitem_iter_and_len_before_instantiation():
    """三个 primitive 分别定义 lookup、key iteration 与 finite size；遗漏时保持 abstract。"""

    class MissingPrimitives(Mapping):
        pass

    assert MissingPrimitives.__abstractmethods__ == {
        "__getitem__",
        "__iter__",
        "__len__",
    }
    with pytest.raises(TypeError, match="abstract method"):
        MissingPrimitives()


def test_mapping_iteration_yields_keys_and_unlocks_normal_read_workflows():
    """Mapping.__iter__ 的合同是 key stream；values/items 由 key 再 lookup 组合。"""

    mapping = ReadOnlyMap([("name", "Ada"), ("language", "Python")])

    assert isinstance(mapping, Mapping)
    assert len(mapping) == 2
    assert list(mapping) == ["name", "language"]
    assert list(mapping.keys()) == ["name", "language"]
    assert list(mapping.values()) == ["Ada", "Python"]
    assert list(mapping.items()) == [
        ("name", "Ada"),
        ("language", "Python"),
    ]
    assert dict(mapping) == {"name": "Ada", "language": "Python"}


def test_returning_values_from_mapping_iter_breaks_default_views():
    """若错误遍历 value，keys view 会照单全收，items view 再把 value 当 key。"""

    class ValueIteratingMap(ReadOnlyMap):
        def __iter__(self):
            return iter(self.storage.values())

    broken = ValueIteratingMap({"first": 10, "second": 20})

    assert list(broken) == [10, 20]
    assert list(broken.keys()) == [10, 20]
    with pytest.raises(KeyError):
        list(broken.items())


def test_get_and_contains_distinguish_missing_keys_from_false_values():
    """存在性取决于 lookup 是否抛 KeyError，与返回 None/0/False 的 truthiness 无关。"""

    mapping = ReadOnlyMap({"none": None, "zero": 0, "false": False})

    assert mapping.get("none", "fallback") is None
    assert mapping.get("zero", "fallback") == 0
    assert mapping.get("missing", "fallback") == "fallback"
    assert "none" in mapping
    assert "zero" in mapping
    assert "missing" not in mapping

    assert mapping.lookups == [
        "none",
        "zero",
        "missing",
        "none",
        "zero",
        "missing",
    ]


def test_get_and_contains_only_catch_keyerror_not_other_lookup_failures():
    """TypeError 或后端 RuntimeError 不是“key 缺失”，mixin 不会错误转成 default/False。"""

    class BackendMap(ReadOnlyMap):
        def __getitem__(self, key):
            if key == "backend":
                raise RuntimeError("backend unavailable")
            return super().__getitem__(key)

    mapping = BackendMap({"name": "Ada"})

    with pytest.raises(TypeError, match="unhashable"):
        mapping.get([], "fallback")
    with pytest.raises(TypeError, match="unhashable"):
        [] in mapping
    with pytest.raises(RuntimeError, match="backend"):
        mapping.get("backend", "fallback")
    with pytest.raises(RuntimeError, match="backend"):
        "backend" in mapping


def test_mapping_default_methods_create_the_three_documented_view_types():
    """Mapping.keys/items/values 每次创建轻量 view，并保留对同一 mapping 的引用。"""

    mapping = ReadOnlyMap({"a": 1})
    keys = mapping.keys()
    items = mapping.items()
    values = mapping.values()

    assert type(keys) is KeysView
    assert type(items) is ItemsView
    assert type(values) is ValuesView
    assert isinstance(keys, MappingView)
    assert isinstance(items, MappingView)
    assert isinstance(values, MappingView)
    assert len(keys) == len(items) == len(values) == 1


def test_existing_mapping_views_reflect_later_storage_changes():
    """先取得 view 再增删底层 dict；同一 view 的长度、membership 和 iteration 都更新。"""

    mapping = ReadOnlyMap([("a", 1), ("b", 2)])
    keys = mapping.keys()
    items = mapping.items()
    values = mapping.values()

    del mapping.storage["a"]
    mapping.storage["c"] = 3

    assert list(keys) == ["b", "c"]
    assert list(items) == [("b", 2), ("c", 3)]
    assert list(values) == [2, 3]
    assert len(keys) == 2
    assert "c" in keys
    assert ("c", 3) in items
    assert 3 in values


def test_keys_view_is_set_like_and_algebra_materializes_builtin_set():
    """KeysView._from_iterable 返回 set；view 本身仍保持 live，不会被运算结果替代。"""

    mapping = ReadOnlyMap([("a", 1), ("b", 2), ("c", 3)])
    keys = mapping.keys()

    assert isinstance(keys, Set)
    assert keys == {"a", "b", "c"}
    assert {"a", "b"} < keys

    intersection = keys & {"b", "c", "d"}
    union = keys | ["d"]
    symmetric = keys ^ {"c", "d"}

    assert type(intersection) is set
    assert intersection == {"b", "c"}
    assert type(union) is set
    assert union == {"a", "b", "c", "d"}
    assert type(symmetric) is set
    assert symmetric == {"a", "b", "d"}


def test_items_view_is_set_like_when_item_pairs_are_hashable():
    """(key, value) 唯一且可哈希时，ItemsView 可安全参与常见集合运算。"""

    mapping = ReadOnlyMap([("a", 1), ("b", 2)])
    items = mapping.items()

    assert isinstance(items, Set)
    assert ("a", 1) in items
    assert ("a", 2) not in items

    intersection = items & {("a", 1), ("c", 3)}
    assert type(intersection) is set
    assert intersection == {("a", 1)}
    assert items == {("a", 1), ("b", 2)}


def test_items_view_membership_checks_value_identity_before_equality():
    """同一 value object 通过 ``is`` 短路，不必调用可能昂贵或失败的 __eq__。"""

    class IdentityOnly:
        def __eq__(self, other):
            raise AssertionError("equality should not run for identical value")

    value = IdentityOnly()
    items = ReadOnlyMap({"token": value}).items()

    assert ("token", value) in items


def test_items_view_can_query_unhashable_values_but_set_materialization_fails():
    """membership 只需 equality；代数结果 set 必须 hash 整个 (key, value) pair。"""

    mapping = ReadOnlyMap({"roles": ["admin"]})
    items = mapping.items()

    assert ("roles", ["admin"]) in items
    assert list(items) == [("roles", ["admin"])]

    with pytest.raises(TypeError, match="unhashable"):
        items & items


def test_values_view_is_a_duplicate_preserving_collection_not_a_set():
    """value 通常不唯一；ValuesView 支持 len/iter/in，但没有集合代数或内容 equality。"""

    mapping = ReadOnlyMap([("first", 1), ("second", 1), ("third", 2)])
    first_view = mapping.values()
    second_view = mapping.values()

    assert isinstance(first_view, Collection)
    assert not isinstance(first_view, Set)
    assert list(first_view) == [1, 1, 2]
    assert 1 in first_view
    assert first_view is not second_view
    assert first_view != second_view

    with pytest.raises(TypeError):
        first_view & {1, 2}


def test_mapping_equality_compares_items_and_ignores_iteration_order():
    """Mapping mixin 把双方 items 转成 dict 比较；具体 key iteration 顺序不影响 equality。"""

    first = ReadOnlyMap([("a", 1), ("b", 2)])
    reversed_order = ReadOnlyMap([("b", 2), ("a", 1)])

    assert first == reversed_order
    assert first == {"a": 1, "b": 2}
    assert first != {"a": 1, "b": 99}
    assert first != [("a", 1), ("b", 2)]


def test_mapping_mixin_disables_reversed_until_concrete_type_implements_it():
    """Mapping.__reversed__ 是 None；built-in dict 的反向能力不是 ABC 自动 mixin。"""

    mapping = ReadOnlyMap([("a", 1), ("b", 2)])

    assert not isinstance(mapping, Reversible)
    with pytest.raises(TypeError, match="not reversible"):
        reversed(mapping)

    class ReversibleMap(ReadOnlyMap):
        def __reversed__(self):
            return reversed(tuple(self.storage))

    reversible = ReversibleMap([("a", 1), ("b", 2)])
    assert isinstance(reversible, Reversible)
    assert list(reversed(reversible)) == ["b", "a"]


def test_mapping_view_base_delegates_length_and_builds_a_readable_repr():
    """MappingView 本身只提供 Sized wrapper；专用 subclass 再补 membership/iteration。"""

    mapping = ReadOnlyMap({"a": 1})
    view = MappingView(mapping)

    assert len(view) == 1
    assert repr(view) == "MappingView(ReadOnlyMap({'a': 1}))"
    assert repr(mapping.keys()) == "KeysView(ReadOnlyMap({'a': 1}))"


def test_mutating_mapping_during_view_iteration_can_invalidate_iterator():
    """view 是 live 的，但已创建的 dict iterator 不允许底层 size 在遍历中改变。"""

    mapping = ReadOnlyMap([("a", 1), ("b", 2)])
    iterator = iter(mapping.keys())

    assert next(iterator) == "a"
    mapping.storage["c"] = 3

    with pytest.raises(RuntimeError, match="changed size"):
        next(iterator)


def test_builtin_dict_views_are_registered_and_add_reversal_and_mapping_proxy():
    """内置 view 通过 ABC 注册，另有 reversed() 与 3.10 ``.mapping`` 扩展。"""

    source = {"a": 1, "b": 2}
    keys = source.keys()
    items = source.items()
    values = source.values()

    assert isinstance(keys, KeysView)
    assert isinstance(items, ItemsView)
    assert isinstance(values, ValuesView)
    assert list(reversed(keys)) == ["b", "a"]
    assert list(reversed(items)) == [("b", 2), ("a", 1)]
    assert list(reversed(values)) == [2, 1]

    proxy = keys.mapping
    assert type(proxy) is MappingProxyType
    assert proxy == source

    source["c"] = 3
    assert proxy["c"] == 3
    with pytest.raises(TypeError):
        proxy["d"] = 4


def test_mapping_proxy_is_a_live_read_only_mapping_with_snapshot_copy():
    """MappingProxyType 阻止代理写入，但继续观察源 mapping；copy() 返回独立浅副本。"""

    source = {"a": 1}
    proxy = MappingProxyType(source)
    snapshot = proxy.copy()

    assert isinstance(proxy, Mapping)
    assert list(proxy) == ["a"]
    assert proxy["a"] == 1

    source["b"] = 2
    assert proxy["b"] == 2
    assert snapshot == {"a": 1}

    merged = proxy | {"a": 10, "c": 3}
    assert type(merged) is dict
    assert merged == {"a": 10, "b": 2, "c": 3}
    assert list(reversed(proxy)) == ["b", "a"]

    with pytest.raises(TypeError):
        proxy["c"] = 3


def test_mapping_and_view_abcs_support_generic_alias_metadata():
    """3.9+ subscription 产生运行时 GenericAlias，origin/args 可供注解 introspection。"""

    mapping_alias = Mapping[str, int]
    keys_alias = KeysView[str]

    assert isinstance(mapping_alias, GenericAlias)
    assert mapping_alias.__origin__ is Mapping
    assert mapping_alias.__args__ == (str, int)
    assert isinstance(keys_alias, GenericAlias)
    assert keys_alias.__origin__ is KeysView
    assert keys_alias.__args__ == (str,)


# ``MutableMapping`` 删除、批量更新与默认值 mixin 示例。
#
# MutableMapping 在只读 Mapping 的三个 primitive 上再要求 ``__setitem__`` 和
# ``__delitem__``。默认 mutation 算法由公开 lookup/iteration/set/delete 组合而成，
# 因此会触发具体实现的 hook，但不提供事务回滚或 built-in dict 的 LIFO popitem。
#
# 本文件的 dict-backed 辅助类型保留 insertion order 只为稳定展示调用路径；ABC 本身
# 不承诺 popitem 顺序。当前文件尚未经过 pytest 验证。

# polyglot-covers: python.collections.abc.MutableMapping python.mutable-mapping.primitives
# polyglot-covers: python.mutable-mapping.pop python.mutable-mapping.pop-default
# polyglot-covers: python.mutable-mapping.popitem python.mutable-mapping.popitem-order
# polyglot-covers: python.mutable-mapping.clear python.mutable-mapping.primitive-dispatch
# polyglot-covers: python.mutable-mapping.update-mapping python.mutable-mapping.update-keys-object
# polyglot-covers: python.mutable-mapping.update-pairs python.mutable-mapping.update-keywords
# polyglot-covers: python.mutable-mapping.update-precedence python.mutable-mapping.partial-update
# polyglot-covers: python.mutable-mapping.validation-failure python.mutable-mapping.malformed-pair
# polyglot-covers: python.mutable-mapping.setdefault python.mutable-mapping.false-values
# polyglot-covers: python.mutable-mapping.missing-fallback python.mutable-mapping.storage-bypass
# polyglot-covers: python.dict.mutable-mapping-registration python.dict.popitem-lifo




class TrackedMapping(MutableMapping):
    """使用 dict 存储并记录默认 mixin 可观察到的 get/set/del/iter primitive。"""

    def __init__(self, values=()):
        self.storage = dict(values)
        self.calls = []

    def __getitem__(self, key):
        self.calls.append(("get", key))
        return self.storage[key]

    def __setitem__(self, key, value):
        self.calls.append(("set", key, value))
        self.storage[key] = value

    def __delitem__(self, key):
        self.calls.append(("del", key))
        del self.storage[key]

    def __iter__(self):
        self.calls.append(("iter",))
        return iter(self.storage)

    def __len__(self):
        return len(self.storage)


def test_mutable_mapping_requires_setitem_and_delitem_in_addition_to_mapping():
    """只实现 get/iter/len 仍是 read-only；两个 mutation primitive 未补齐就不能实例化。"""

    class ReadOnlyImplementation(MutableMapping):
        def __getitem__(self, key):
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self):
            return 0

    assert ReadOnlyImplementation.__abstractmethods__ == {
        "__delitem__",
        "__setitem__",
    }
    with pytest.raises(TypeError, match="abstract method"):
        ReadOnlyImplementation()


def test_pop_reads_then_deletes_existing_key_and_returns_false_value():
    """值为 0 不代表缺失；pop 先 get，再 del，并返回原值。"""

    mapping = TrackedMapping({"retries": 0, "enabled": False})

    assert mapping.pop("retries") == 0
    assert mapping.storage == {"enabled": False}
    assert mapping.calls == [
        ("get", "retries"),
        ("del", "retries"),
    ]


def test_pop_without_default_preserves_keyerror_and_does_not_delete():
    """lookup 的 KeyError 直接向外传播；失败路径不会调用 __delitem__。"""

    mapping = TrackedMapping({"name": "Ada"})

    with pytest.raises(KeyError) as error:
        mapping.pop("missing")

    assert error.value.args == ("missing",)
    assert mapping.storage == {"name": "Ada"}
    assert mapping.calls == [("get", "missing")]


def test_pop_explicit_default_including_none_distinguishes_missing_key():
    """私有 sentinel 区分“没传 default”与“显式 default=None”；两者异常语义不同。"""

    mapping = TrackedMapping({"name": "Ada"})
    marker = object()

    assert mapping.pop("first", None) is None
    assert mapping.pop("second", marker) is marker
    assert mapping.storage == {"name": "Ada"}
    assert mapping.calls == [
        ("get", "first"),
        ("get", "second"),
    ]


def test_popitem_uses_first_key_from_this_concrete_iteration_then_gets_and_deletes():
    """mixin 只调用 next(iter(self))；本辅助类型按 insertion order，故这里弹出 first。"""

    mapping = TrackedMapping([("first", 1), ("second", 2)])

    assert mapping.popitem() == ("first", 1)
    assert mapping.storage == {"second": 2}
    assert mapping.calls == [
        ("iter",),
        ("get", "first"),
        ("del", "first"),
    ]


def test_empty_popitem_raises_keyerror_before_get_or_delete():
    """空 iterator 的 StopIteration 被转成无额外异常上下文的 KeyError。"""

    mapping = TrackedMapping()

    with pytest.raises(KeyError):
        mapping.popitem()
    assert mapping.calls == [("iter",)]


def test_builtin_dict_overrides_popitem_with_lifo_order():
    """dict 是 MutableMapping，但它的 C 实现覆盖 mixin；3.7+ popitem 保证最后项优先。"""

    custom = TrackedMapping([("first", 1), ("second", 2)])
    builtin = {"first": 1, "second": 2}

    assert isinstance(custom, MutableMapping)
    assert isinstance(builtin, MutableMapping)
    assert custom.popitem() == ("first", 1)
    assert builtin.popitem() == ("second", 2)


def test_clear_repeatedly_calls_popitem_until_empty_and_returns_none():
    """默认 clear 反复组合 iter/get/del，最终以空 popitem 的 KeyError 正常收尾。"""

    mapping = TrackedMapping([("a", 1), ("b", 2)])

    assert mapping.clear() is None
    assert mapping.storage == {}
    assert mapping.calls == [
        ("iter",),
        ("get", "a"),
        ("del", "a"),
        ("iter",),
        ("get", "b"),
        ("del", "b"),
        ("iter",),
    ]


def test_update_mapping_branch_iterates_source_keys_then_looks_up_each_value():
    """真正 Mapping 走 isinstance 分支；source 提供 key stream，target 逐项 __setitem__。"""

    source = TrackedMapping([("theme", "dark"), ("timeout", 10)])
    target = TrackedMapping({"theme": "light"})

    assert target.update(source) is None
    assert target.storage == {"theme": "dark", "timeout": 10}
    assert source.calls == [
        ("iter",),
        ("get", "theme"),
        ("get", "timeout"),
    ]
    assert target.calls == [
        ("set", "theme", "dark"),
        ("set", "timeout", 10),
    ]


def test_update_keys_object_branch_supports_unregistered_mapping_like_sources():
    """非 Mapping 只要有 keys()，就按 key lookup；不会把对象本身当 pair iterable。"""

    class LegacyConfig:
        def __init__(self):
            self.data = {"language": "Python", "version": "3.10"}
            self.calls = []

        def keys(self):
            self.calls.append(("keys",))
            return self.data.keys()

        def __getitem__(self, key):
            self.calls.append(("get", key))
            return self.data[key]

        def __iter__(self):
            raise AssertionError("keys() branch should not iterate the source")

    source = LegacyConfig()
    target = TrackedMapping()

    target.update(source)

    assert not isinstance(source, Mapping)
    assert source.calls == [
        ("keys",),
        ("get", "language"),
        ("get", "version"),
    ]
    assert target.storage == {"language": "Python", "version": "3.10"}


def test_update_pair_iterable_then_keywords_apply_in_order_with_keywords_last():
    """无 keys() 时逐 pair unpack；随后 keyword 写入，因此同名 mode 最终取 CLI 值。"""

    target = TrackedMapping({"existing": True})
    pairs = ((key, value) for key, value in [
        ("mode", "file"),
        ("timeout", 10),
    ])

    assert target.update(pairs, mode="cli", debug=False) is None
    assert target.storage == {
        "existing": True,
        "mode": "cli",
        "timeout": 10,
        "debug": False,
    }
    assert target.calls == [
        ("set", "mode", "file"),
        ("set", "timeout", 10),
        ("set", "mode", "cli"),
        ("set", "debug", False),
    ]


def test_malformed_pair_leaves_earlier_update_writes_in_place():
    """MutableMapping.update 没有事务；第二个 pair unpack 失败不会回滚第一个 set。"""

    target = TrackedMapping({"before": 0})
    malformed = [("accepted", 1), ("missing-value",)]

    with pytest.raises(ValueError, match="not enough values"):
        target.update(malformed)

    assert target.storage == {"before": 0, "accepted": 1}
    assert target.calls == [("set", "accepted", 1)]


def test_noniterable_update_source_raises_typeerror_without_writing():
    """没有 Mapping 身份、keys() 或 pair iteration 的输入不能被 update 消费。"""

    target = TrackedMapping({"before": 0})

    with pytest.raises(TypeError, match="not iterable"):
        target.update(42)

    assert target.storage == {"before": 0}
    assert target.calls == []


def test_validation_failure_during_update_is_also_non_atomic():
    """具体 __setitem__ 可维护领域规则；中途拒绝值时，早先通过的项已经提交。"""

    class PercentageMapping(TrackedMapping):
        def __setitem__(self, key, value):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError("percentage must be int")
            if not 0 <= value <= 100:
                raise ValueError("percentage out of range")
            super().__setitem__(key, value)

    percentages = PercentageMapping()

    with pytest.raises(ValueError, match="out of range"):
        percentages.update([
            ("completed", 80),
            ("invalid", 101),
            ("never-reached", 50),
        ])

    assert percentages.storage == {"completed": 80}
    assert percentages.calls == [("set", "completed", 80)]


def test_setdefault_existing_false_value_only_reads_and_does_not_write():
    """已存在值为 0 仍直接返回；truthiness 不参与，__setitem__ 不被调用。"""

    mapping = TrackedMapping({"retries": 0})

    assert mapping.setdefault("retries", 3) == 0
    assert mapping.storage == {"retries": 0}
    assert mapping.calls == [("get", "retries")]


def test_setdefault_missing_key_reads_then_sets_default_and_returns_it():
    """仅 KeyError 分支写 default；默认省略时写入并返回 None。"""

    mapping = TrackedMapping()

    assert mapping.setdefault("timeout", 30) == 30
    assert mapping.setdefault("owner") is None
    assert mapping.storage == {"timeout": 30, "owner": None}
    assert mapping.calls == [
        ("get", "timeout"),
        ("set", "timeout", 30),
        ("get", "owner"),
        ("set", "owner", None),
    ]


def test_missing_lookup_fallback_prevents_setdefault_from_inserting():
    """若 __getitem__ 对缺失 key 返回 fallback 而非 KeyError，mixin 会认为 key 已存在。"""

    class DefaultingMapping(TrackedMapping):
        def __getitem__(self, key):
            try:
                return super().__getitem__(key)
            except KeyError:
                return "<unset>"

    mapping = DefaultingMapping()

    assert mapping.setdefault("language", "Python") == "<unset>"
    assert mapping.storage == {}
    assert mapping.calls == [("get", "language")]


def test_direct_storage_mutation_bypasses_setitem_domain_validation():
    """mixin 会走 hook，但公开 storage 是逃生口，具体实现必须自行封装。"""

    class StringKeyMapping(TrackedMapping):
        def __setitem__(self, key, value):
            if not isinstance(key, str):
                raise TypeError("key must be str")
            super().__setitem__(key, value)

    mapping = StringKeyMapping()
    mapping["safe"] = 1

    with pytest.raises(TypeError, match="key must be str"):
        mapping[42] = "blocked"

    mapping.storage[42] = "bypassed"
    assert mapping.storage == {"safe": 1, 42: "bypassed"}
