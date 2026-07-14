"""054｜``MutableMapping`` 删除、批量更新与默认值 mixin 示例。

MutableMapping 在只读 Mapping 的三个 primitive 上再要求 ``__setitem__`` 和
``__delitem__``。默认 mutation 算法由公开 lookup/iteration/set/delete 组合而成，
因此会触发具体实现的 hook，但不提供事务回滚或 built-in dict 的 LIFO popitem。

本文件的 dict-backed 辅助类型保留 insertion order 只为稳定展示调用路径；ABC 本身
不承诺 popitem 顺序。当前文件尚未经过 pytest 验证。
"""

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

from collections.abc import Mapping
from collections.abc import MutableMapping

import pytest


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
