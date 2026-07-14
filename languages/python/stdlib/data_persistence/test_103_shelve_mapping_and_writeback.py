"""103｜``shelve`` persistent mapping、pickle value 与 writeback cache。

shelf 的 key 始终是 str，value 则通过 pickle 存为 bytes。读取 value 得到反序列化副本；
``writeback=False`` 时原地修改不会持久化，``writeback=True`` 虽方便，却会缓存并重写所有
读取过的 entry。底层 DBM 格式与文件后缀依平台而异，始终通过 shelve 自己重新打开。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.shelve.open python.shelve.context-manager
# polyglot-covers: python.shelve.Shelf python.shelve.MutableMapping
# polyglot-covers: python.shelve.string-keys python.shelve.pickled-values
# polyglot-covers: python.shelve.keyencoding python.shelve.underlying-bytes
# polyglot-covers: python.shelve.python310-default-protocol python.shelve.explicit-protocol
# polyglot-covers: python.shelve.value-copy python.shelve.mutable-reassignment
# polyglot-covers: python.shelve.writeback-false python.shelve.in-place-mutation-trap
# polyglot-covers: python.shelve.writeback-true python.shelve.cache
# polyglot-covers: python.shelve.sync python.shelve.writeback-all-accessed
# polyglot-covers: python.shelve.close python.shelve.closed-operation
# polyglot-covers: python.shelve.flags-c-r-w-n python.shelve.new-empty-database
# polyglot-covers: python.shelve.DbfilenameShelf python.shelve.backend-opacity
# polyglot-covers: python.shelve.unpicklable-value python.shelve.trusted-data-only
# polyglot-covers: python.shelve.BsdDbShelf python.shelve.optional-navigation

import dbm
import pickle
import shelve

import pytest


class CountingBytesMapping(dict):
    """记录 Shelf 对 underlying DBM-like mapping 的实际 writes。"""

    def __init__(self):
        super().__init__()
        self.written_keys = []

    def __setitem__(self, key, value):
        self.written_keys.append(key)
        return super().__setitem__(key, value)


def test_shelf_wraps_a_bytes_mapping_with_string_keys_and_pickled_values():
    """Shelf 是 adapter：公开层看到 Python objects，底层 mapping 只看到 encoded key/pickle bytes。"""

    backing = {}
    with shelve.Shelf(backing) as shelf:
        shelf["record"] = {"name": "Ada", "scores": [1, 2]}

        assert shelf["record"] == {"name": "Ada", "scores": [1, 2]}
        assert list(shelf) == ["record"]
        assert len(shelf) == 1

    assert set(backing) == {b"record"}
    assert isinstance(backing[b"record"], bytes)
    assert pickle.loads(backing[b"record"]) == {
        "name": "Ada",
        "scores": [1, 2],
    }


def test_shelf_supports_common_mutable_mapping_operations():
    """get/setdefault/update/pop/del 适合从 dict 迁移；不存在 key 保持 KeyError 语义。"""

    with shelve.Shelf({}) as shelf:
        shelf.update({"a": 1, "b": 2})
        assert shelf.get("a") == 1
        assert shelf.get("missing", 99) == 99
        assert shelf.setdefault("c", 3) == 3
        assert shelf.pop("b") == 2
        del shelf["a"]

        assert dict(shelf) == {"c": 3}
        with pytest.raises(KeyError):
            _ = shelf["missing"]


def test_shelf_keys_must_be_strings():
    """value 可以是广泛的 pickle object，key 却必须能按 keyencoding 调用 str.encode。"""

    with shelve.Shelf({}) as shelf:
        with pytest.raises((AttributeError, TypeError)):
            shelf[b"bytes-key"] = "value"
        with pytest.raises((AttributeError, TypeError)):
            shelf[42] = "value"


def test_keyencoding_controls_the_underlying_bytes_and_iteration_decodes_them():
    """同一 DBM file 必须始终用同一 keyencoding，否则 bytes key 会被错误解释或无法 decode。"""

    backing = {}
    with shelve.Shelf(backing, keyencoding="latin-1") as shelf:
        shelf["café"] = "value"
        assert list(shelf.keys()) == ["café"]

    assert b"caf\xe9" in backing


def test_python_310_default_shelf_protocol_is_pickle_default_protocol():
    """3.10 起 protocol=None 跟随 pickle.DEFAULT_PROTOCOL；长期数据仍宜显式固定兼容版本。"""

    default_backing = {}
    protocol_zero_backing = {}
    with shelve.Shelf(default_backing) as shelf:
        shelf["item"] = [1, 2]
    with shelve.Shelf(protocol_zero_backing, protocol=0) as shelf:
        shelf["item"] = [1, 2]

    assert default_backing[b"item"].startswith(
        bytes((0x80, pickle.DEFAULT_PROTOCOL))
    )
    assert not protocol_zero_backing[b"item"].startswith(b"\x80")
    assert pickle.loads(default_backing[b"item"]) == [1, 2]
    assert pickle.loads(protocol_zero_backing[b"item"]) == [1, 2]


def test_reading_a_shelf_value_returns_a_new_unpickled_copy_each_time():
    """writeback=False 时没有 identity map；同一 key 的两次读取 value 相同但 object 不同。"""

    with shelve.Shelf({}) as shelf:
        shelf["items"] = [1, 2]
        first = shelf["items"]
        second = shelf["items"]

        assert first == second == [1, 2]
        assert first is not second


def test_in_place_mutation_is_lost_without_reassignment_when_writeback_is_false():
    """``shelf[key].append`` 改的是临时副本；Shelf 无法观察这个 mutable object 后续发生了什么。"""

    backing = {}
    with shelve.Shelf(backing, writeback=False) as shelf:
        shelf["items"] = [1]
        shelf["items"].append(2)

        assert shelf["items"] == [1]


def test_extract_mutate_reassign_is_the_explicit_low_memory_workflow():
    """默认模式下只在真正改变的 key 上写回，适合 shelf 很大而修改集合很小的场景。"""

    backing = {}
    with shelve.Shelf(backing, writeback=False) as shelf:
        shelf["items"] = [1]
        items = shelf["items"]
        items.append(2)
        shelf["items"] = items

        assert shelf["items"] == [1, 2]


def test_writeback_true_persists_in_place_mutation_on_sync():
    """读取后 object 留在 memory cache；sync 写回并清空 cache，而不必重新 assignment。"""

    backing = {}
    with shelve.Shelf(backing, writeback=True) as shelf:
        shelf["items"] = [1]
        cached = shelf["items"]
        cached.append(2)

        assert pickle.loads(backing[b"items"]) == [1]
        assert shelf.sync() is None
        assert pickle.loads(backing[b"items"]) == [1, 2]
        assert shelf["items"] == [1, 2]
        assert shelf["items"] is not cached


def test_writeback_sync_rewrites_every_accessed_entry_even_when_unchanged():
    """cache 不追踪 dirty bit；只读过的 entry 也会在 sync/close 序列化并写回。"""

    backing = CountingBytesMapping()
    with shelve.Shelf(backing, writeback=True) as shelf:
        shelf["a"] = [1]
        shelf["b"] = [2]
        backing.written_keys.clear()

        _ = shelf["a"]
        _ = shelf["b"]
        shelf.sync()

        assert backing.written_keys == [b"a", b"b"]


def test_writeback_close_persists_cached_changes_and_context_closes_shelf():
    """close 会先 sync；退出后任何 mapping operation 都按 closed shelf 规则报 ValueError。"""

    backing = {}
    shelf = shelve.Shelf(backing, writeback=True)
    with shelf:
        shelf["items"] = [1]
        shelf["items"].append(2)

    assert pickle.loads(backing[b"items"]) == [1, 2]
    with pytest.raises(ValueError):
        _ = shelf["items"]
    with pytest.raises(ValueError):
        shelf["other"] = 3


def test_unpicklable_value_is_rejected_before_underlying_mapping_assignment():
    """Shelf 继承 pickle 的能力与安全边界；lambda 无稳定 global name，不能作为 value。"""

    backing = {}
    with shelve.Shelf(backing) as shelf:
        with pytest.raises(pickle.PicklingError):
            shelf["callable"] = lambda value: value

        assert "callable" not in shelf
        assert b"callable" not in backing


def test_shelve_open_persists_objects_across_close_and_reopen(tmp_path):
    """filename 是 backend base name，可能产生一个或多个带 suffix 文件；不要自己猜实际 DBM 文件。"""

    base_name = str(tmp_path / "application-shelf")
    with shelve.open(base_name, flag="c") as shelf:
        assert isinstance(shelf, shelve.DbfilenameShelf)
        shelf["record"] = {"name": "Ada", "values": [1, 2]}

    with shelve.open(base_name, flag="r") as shelf:
        assert shelf["record"] == {"name": "Ada", "values": [1, 2]}

    assert any(tmp_path.iterdir())


def test_open_flag_n_discards_existing_entries_and_creates_a_new_empty_shelf(tmp_path):
    """``n`` 不是 create-if-missing；它总是建立新数据库，会丢弃同 base name 的旧内容。"""

    base_name = str(tmp_path / "resettable-shelf")
    with shelve.open(base_name, flag="c") as shelf:
        shelf["old"] = "value"

    with shelve.open(base_name, flag="n") as shelf:
        assert list(shelf) == []
        shelf["new"] = "value"

    with shelve.open(base_name, flag="r") as shelf:
        assert dict(shelf) == {"new": "value"}


def test_open_read_flag_requires_an_existing_database(tmp_path):
    """``r`` 与 ``w`` 都不创建 missing database；首次初始化应显式选 c 或 n。"""

    base_name = str(tmp_path / "missing-shelf")

    with pytest.raises(dbm.error):
        shelve.open(base_name, flag="r")
    with pytest.raises(dbm.error):
        shelve.open(base_name, flag="w")


def test_bsd_db_shelf_exposes_optional_navigation_surface():
    """BsdDbShelf 依赖 third-party bsddb-like mapping；仅在 backend 支持时才可使用有序导航。"""

    assert issubclass(shelve.BsdDbShelf, shelve.Shelf)
    for method_name in ("first", "next", "previous", "last", "set_location"):
        assert callable(getattr(shelve.BsdDbShelf, method_name))
