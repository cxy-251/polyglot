"""064｜``shelve`` persistent mapping、pickle value 与 writeback cache。

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
import io
import marshal
import importlib
from dbm import dumb

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
    # writeback=True 的 __setitem__ 会先缓存再写 backing；closed 写入若失败，
    # 遗留 cache 会使 __del__ 再次 sync 并产生 unraisable warning。
    shelf.writeback = False
    with pytest.raises(ValueError):
        shelf["other"] = 3


def test_unpicklable_value_is_rejected_before_underlying_mapping_assignment():
    """Shelf 继承 pickle 的能力与安全边界；lambda 无稳定 global name，不能作为 value。"""

    backing = {}
    with shelve.Shelf(backing) as shelf:
        with pytest.raises((pickle.PicklingError, AttributeError)):
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


# ``marshal`` 的受限类型、format version 与内部用途边界。
#
# marshal 主要服务 ``.pyc`` code object，不是通用持久化格式：它不支持普通
# class instance，格式也不承诺跨 Python 版本兼容。version 3 起才记录共享
# identity/递归引用。和 pickle 一样，
# 不要读取不可信 marshal bytes；本文件只加载自己刚生成的隔离数据。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.marshal.dumps python.marshal.loads python.marshal.binary-format
# polyglot-covers: python.marshal.dump python.marshal.load python.marshal.binary-file
# polyglot-covers: python.marshal.supported-scalars python.marshal.supported-containers
# polyglot-covers: python.marshal.None python.marshal.Ellipsis python.marshal.StopIteration
# polyglot-covers: python.marshal.code-object python.marshal.pyc-purpose
# polyglot-covers: python.marshal.unsupported-instance python.marshal.ValueError
# polyglot-covers: python.marshal.dump-partial-garbage python.marshal.unsupported-substitution
# polyglot-covers: python.marshal.version python.marshal.format-zero-to-four
# polyglot-covers: python.marshal.version-three-recursion python.marshal.object-instancing
# polyglot-covers: python.marshal.shared-reference python.marshal.recursive-list
# polyglot-covers: python.marshal.bytes-like-input python.marshal.trailing-bytes
# polyglot-covers: python.marshal.sequential-values python.marshal.EOFError
# polyglot-covers: python.marshal.invalid-data python.marshal.not-general-persistence
# polyglot-covers: python.marshal.trusted-data-only python.marshal.version-compatibility-trap




class UnsupportedRecord:
    def __init__(self, value):
        self.value = value


def test_supported_scalar_values_round_trip_with_their_python_types():
    """marshal 的 builtin allowlist 较窄，但常见数值、文本与 binary scalar 可保存。"""

    values = [
        None,
        True,
        False,
        0,
        2**100,
        -3.5,
        2 + 4j,
        "中文",
        b"bytes",
        bytearray(b"mutable"),
    ]

    for value in values:
        restored = marshal.loads(marshal.dumps(value))
        assert restored == value
        if isinstance(value, bytearray):
            assert type(restored) is bytes
        else:
            assert type(restored) is type(value)
    # 3.10 marshal 把 bytearray 规范化为 bytes；它保存值而不承诺保留
    # 所有相似二进制容器的具体类型。


def test_supported_containers_round_trip_when_every_member_is_supported():
    """container 本身在 allowlist 还不够，所有递归 members 也必须可 marshal。"""

    original = {
        "tuple": (1, "two"),
        "list": [3, 4],
        "set": {5, 6},
        "frozenset": frozenset({7, 8}),
        "nested": [{"key": b"value"}],
    }

    restored = marshal.loads(marshal.dumps(original))

    assert restored == original
    assert isinstance(restored["tuple"], tuple)
    assert isinstance(restored["frozenset"], frozenset)


def test_special_singletons_keep_identity():
    """None、Ellipsis 与 StopIteration 在 marshal format 中有专用表示。"""

    assert marshal.loads(marshal.dumps(None)) is None
    assert marshal.loads(marshal.dumps(Ellipsis)) is Ellipsis
    assert marshal.loads(marshal.dumps(StopIteration)) is StopIteration


def test_code_objects_are_a_primary_marshal_use_case():
    """marshal 保存 bytecode fields；这里只执行测试自己 compile 的可信 expression。"""

    code = compile("40 + 2", "<polyglot>", "eval")

    restored = marshal.loads(marshal.dumps(code))

    assert restored.co_filename == "<polyglot>"
    assert restored.co_code == code.co_code
    assert eval(restored, {}) == 42


def test_custom_class_instances_are_not_supported():
    """marshal 不按 qualified name 保存 instance；通用对象持久化应选 pickle。"""

    with pytest.raises(ValueError):
        marshal.dumps(UnsupportedRecord("value"))


def test_nested_unsupported_value_makes_dumps_fail():
    """错误可出现在 object graph 深处；不能仅检查 root container 的类型。"""

    with pytest.raises(ValueError):
        marshal.dumps({"valid": 1, "invalid": UnsupportedRecord("value")})


def test_dump_validates_before_calling_file_write_for_an_unsupported_member():
    """3.10 先构造完整 bytes；编码失败时不会调用 Python file.write。"""

    stream = io.BytesIO()

    with pytest.raises(ValueError):
        marshal.dump([1, UnsupportedRecord("value"), 3], stream)

    assert stream.tell() == 0
    # 文档仍警告失败后可能留下 garbage；调用方不应把这个实现细节
    # 当成跨版本事务保证，最稳妥的做法仍是写临时文件后原子替换。


def test_dump_and_load_round_trip_through_a_binary_file(tmp_path):
    """file API 要求 binary stream；3.10 转发 write 的字节数返回值。"""

    path = tmp_path / "value.marshal"
    with path.open("wb") as stream:
        returned = marshal.dump({"value": [1, 2, 3]}, stream)

    with path.open("rb") as stream:
        restored = marshal.load(stream)

    assert returned == path.stat().st_size
    assert restored == {"value": [1, 2, 3]}


def test_dump_rejects_a_text_stream():
    """marshal bytes 不是字符编码结果，不应 decode 后写入 StringIO/text file。"""

    with pytest.raises(TypeError):
        marshal.dump({"value": 1}, io.StringIO())


def test_python_310_current_format_version_is_four():
    """marshal.version 描述当前 writer format，不是兼容承诺或协议协商。"""

    assert marshal.version == 4


def test_all_documented_python_310_format_versions_round_trip_simple_values():
    """显式旧 version 只改变 encoding features；reader 自动识别 stream 内的表示。"""

    original = {"text": "value", "numbers": [1, 2, 3.5]}

    for version in range(marshal.version + 1):
        payload = marshal.dumps(original, version)
        assert marshal.loads(payload) == original


def test_version_three_adds_shared_object_identity():
    """version 0–2 重复编码 shared value；3+ 用 reference 恢复同一对象。"""

    shared = ["item"]
    original = [shared, shared]

    restored_v2 = marshal.loads(marshal.dumps(original, 2))
    restored_v3 = marshal.loads(marshal.dumps(original, 3))

    assert restored_v2[0] == restored_v2[1]
    assert restored_v2[0] is not restored_v2[1]
    assert restored_v3[0] is restored_v3[1]


def test_recursive_containers_require_format_version_three_or_later():
    """旧 format 没有 back-reference，不能表示 cycle；3/4 恢复 self edge。"""

    recursive = []
    recursive.append(recursive)

    with pytest.raises(ValueError):
        marshal.dumps(recursive, 2)

    for version in (3, 4):
        restored = marshal.loads(marshal.dumps(recursive, version))
        assert restored[0] is restored


def test_loads_accepts_bytes_like_input_and_ignores_trailing_bytes():
    """找到一个完整 value 后不会验证 remainder；外层格式要负责 framing。"""

    payload = marshal.dumps({"value": 1})

    assert marshal.loads(bytearray(payload)) == {"value": 1}
    assert marshal.loads(memoryview(payload)) == {"value": 1}
    assert marshal.loads(payload + b"unvalidated trailing data") == {"value": 1}


def test_multiple_marshaled_values_can_be_loaded_sequentially_from_one_file():
    """连续 dump 可形成 record stream；每次 load 消费一个 value，最终 EOFError。"""

    stream = io.BytesIO()
    marshal.dump("first", stream)
    marshal.dump({"second": 2}, stream)
    stream.seek(0)

    assert marshal.load(stream) == "first"
    assert marshal.load(stream) == {"second": 2}
    with pytest.raises(EOFError):
        marshal.load(stream)


def test_invalid_or_empty_input_uses_more_than_one_failure_type():
    """没有统一 MarshalError；caller 需处理 EOFError/ValueError/TypeError 等错误。"""

    with pytest.raises(EOFError):
        marshal.loads(b"")
    with pytest.raises(ValueError):
        marshal.loads(b"?")
    with pytest.raises(TypeError):
        marshal.loads("not bytes")


# ``dbm`` 的 bytes mapping、后端选择与打开模式。
#
# ``dbm`` 是多个不兼容磁盘格式之上的统一入口。它只保存 bytes，不负责 Python
# 对象序列化；字符串会用默认编码隐式转成 bytes。具体后端取决于 Python 构建环境，所以
# 案例只依赖文档承诺的交集，不假定文件扩展名或异常的某个具体 subclass。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.dbm.open python.dbm.backend-selection python.dbm.whichdb
# polyglot-covers: python.dbm.bytes-mapping python.dbm.string-coercion python.dbm.default-encoding
# polyglot-covers: python.dbm.keys python.dbm.contains python.dbm.get python.dbm.setdefault
# polyglot-covers: python.dbm.delete python.dbm.KeyError python.dbm.type-restriction
# polyglot-covers: python.dbm.flag-r python.dbm.flag-w python.dbm.flag-c python.dbm.flag-n
# polyglot-covers: python.dbm.read-only python.dbm.missing-database python.dbm.persistence
# polyglot-covers: python.dbm.context-manager python.dbm.close python.dbm.error-tuple
# polyglot-covers: python.dbm.backend-file-format python.dbm.not-object-serialization




def test_error_is_a_tuple_covering_backend_specific_exceptions():
    """``dbm.error`` 可直接交给 except/pytest，不必先知道实际后端。"""

    assert isinstance(dbm.error, tuple)
    assert dbm.error
    assert all(isinstance(error_type, type) for error_type in dbm.error)
    assert all(issubclass(error_type, BaseException) for error_type in dbm.error)


def test_new_database_behaves_like_a_bytes_mapping(tmp_path):
    """key/value 的稳定存储类型都是 bytes；这与普通 dict 保存原对象不同。"""

    path = tmp_path / "cache"
    with dbm.open(str(path), "c") as database:
        database[b"language"] = b"Python"
        database[b"year"] = b"1991"

        assert database[b"language"] == b"Python"
        assert set(database.keys()) == {b"language", b"year"}
        assert len(database) == 2


def test_strings_are_encoded_but_reads_still_return_bytes(tmp_path):
    """str 的便利转换容易造成陷阱：读取结果不会自动 decode 回 str。"""

    path = tmp_path / "encoded"
    with dbm.open(str(path), "c") as database:
        database["中文键"] = "中文值"

        assert database["中文键"] == "中文值".encode()
        assert database["中文键"] != "中文值"
        assert "中文键" in database
        assert "中文键".encode() in database


def test_get_and_setdefault_follow_mapping_semantics(tmp_path):
    """所有后端都提供 get/setdefault；用 bytes default 可保持返回类型跨后端一致。"""

    path = tmp_path / "defaults"
    with dbm.open(str(path), "c") as database:
        assert database.get("missing") is None
        assert database.get("missing", b"fallback") == b"fallback"

        # dbm.dumb 继承 MutableMapping.setdefault：缺失时可能原样返回传入 default。
        # 因此可移植代码应传 bytes；无论具体后端如何实现，读取与返回就都是 bytes。
        assert database.setdefault("status", b"new") == b"new"
        assert database.setdefault("status", b"ignored") == b"new"
        assert database[b"status"] == b"new"


def test_assignment_replaces_the_complete_value(tmp_path):
    """DBM 没有嵌套对象或原地修改；同一 key 再赋值就是替换 bytes record。"""

    path = tmp_path / "replace"
    with dbm.open(str(path), "c") as database:
        database["key"] = "old"
        database["key"] = "new"

        assert database["key"] == b"new"
        assert len(database) == 1


def test_delete_and_missing_lookup_use_key_error(tmp_path):
    """普通 mapping 错误用 KeyError；底层 I/O/打开错误才由 backend error 表示。"""

    path = tmp_path / "deletion"
    with dbm.open(str(path), "c") as database:
        database["key"] = "value"
        del database["key"]

        assert "key" not in database
        with pytest.raises(KeyError):
            _ = database["key"]
        with pytest.raises(KeyError):
            del database["key"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (1, b"value"),
        (b"key", 1),
        (("tuple",), b"value"),
    ],
)
def test_only_bytes_and_strings_are_valid_keys_and_values(tmp_path, key, value):
    """dbm 不会 pickle 任意对象；调用者必须先选择自己的编码格式。"""

    path = tmp_path / "types"
    with dbm.open(str(path), "c") as database:
        with pytest.raises(TypeError):
            database[key] = value


def test_context_manager_closes_after_persisting_records(tmp_path):
    """with 负责 close；重开是观察持久化的可移植方式。"""

    path = tmp_path / "persistent"
    with dbm.open(str(path), "c") as database:
        database["answer"] = "42"

    with dbm.open(str(path), "r") as reopened:
        assert reopened["answer"] == b"42"


def test_c_mode_opens_existing_database_without_clearing_it(tmp_path):
    """``c`` 的含义是 create-if-missing，不是每次创建全新数据库。"""

    path = tmp_path / "create-if-missing"
    with dbm.open(str(path), "c") as database:
        database["kept"] = "yes"

    with dbm.open(str(path), "c") as reopened:
        assert reopened["kept"] == b"yes"


def test_n_mode_always_replaces_an_existing_database(tmp_path):
    """需要确定清空旧内容时使用 ``n``；``c`` 不提供这个保证。"""

    path = tmp_path / "replace-all"
    with dbm.open(str(path), "c") as database:
        database["old"] = "record"

    with dbm.open(str(path), "n") as replacement:
        assert list(replacement.keys()) == []
        replacement["new"] = "record"

    with dbm.open(str(path), "r") as reopened:
        assert set(reopened.keys()) == {b"new"}


def test_w_mode_updates_an_existing_database(tmp_path):
    """``w`` 允许读写但要求数据库已存在，适合拒绝意外创建拼错的路径。"""

    path = tmp_path / "existing"
    with dbm.open(str(path), "c") as database:
        database["counter"] = "1"

    with dbm.open(str(path), "w") as database:
        database["counter"] = "2"

    with dbm.open(str(path), "r") as reopened:
        assert reopened["counter"] == b"2"


def test_r_mode_rejects_mutation_with_a_backend_error(tmp_path):
    """只读写入的具体异常随后端变化；统一捕获 ``dbm.error`` 才可移植。"""

    path = tmp_path / "read-only"
    with dbm.open(str(path), "c") as database:
        database["key"] = "value"

    with dbm.open(str(path), "r") as read_only:
        assert read_only["key"] == b"value"
        with pytest.raises(dbm.error):
            read_only["key"] = "changed"
        with pytest.raises(dbm.error):
            del read_only["key"]


@pytest.mark.parametrize("flag", ["r", "w"])
def test_r_and_w_modes_do_not_create_a_missing_database(tmp_path, flag):
    """``r``/``w`` 都不是创建模式；失败类型由可用 backend 决定。"""

    path = tmp_path / f"missing-{flag}"

    with pytest.raises(dbm.error):
        dbm.open(str(path), flag)


def test_whichdb_reports_none_for_a_missing_path(tmp_path):
    """None 表示不可读取/不存在；空字符串表示格式无法识别。"""

    assert dbm.whichdb(str(tmp_path / "missing")) is None


def test_whichdb_identifies_the_backend_that_created_a_database(tmp_path):
    """格式互不兼容；重开现有库时 generic ``open`` 用该结果选择模块。"""

    path = tmp_path / "identified"
    with dbm.open(str(path), "c") as database:
        database["key"] = "value"

    backend_name = dbm.whichdb(str(path))

    assert backend_name in {"dbm.gnu", "dbm.ndbm", "dbm.dumb"}


def test_whichdb_returns_empty_string_for_an_unknown_existing_format(tmp_path):
    """随机普通文件不是 DBM；调用者应区分 unknown format 和 missing path。"""

    path = tmp_path / "not-a-database"
    path.write_bytes(b"plain text, not a DBM file")

    assert dbm.whichdb(str(path)) == ""


# ``dbm.gnu``、``dbm.ndbm`` 与 ``dbm.dumb`` 的能力边界。
#
# GNU/ndbm 依赖 Python 构建时找到的系统库，不能假定所有容器都有；相关测试在模块
# 不可用时明确 skip。``dbm.dumb`` 是纯 Python 最后备选，格式可移植但不面向高性能或
# 数据库。三种格式彼此不兼容，业务代码通常应从通用 ``dbm.open`` 进入。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.dbm.gnu python.dbm.gnu.optional python.dbm.gnu.open-flags
# polyglot-covers: python.dbm.gnu.firstkey python.dbm.gnu.nextkey python.dbm.gnu.unsorted
# polyglot-covers: python.dbm.gnu.sync python.dbm.gnu.reorganize python.dbm.gnu.mapping-limits
# polyglot-covers: python.dbm.ndbm python.dbm.ndbm.optional python.dbm.ndbm.library
# polyglot-covers: python.dbm.ndbm.open python.dbm.ndbm.mapping-limits
# polyglot-covers: python.dbm.dumb python.dbm.dumb.portable-fallback python.dbm.dumb.files
# polyglot-covers: python.dbm.dumb.mutable-mapping python.dbm.dumb.sync python.dbm.dumb.flags
# polyglot-covers: python.dbm.backend-incompatibility python.dbm.platform-availability





def _optional_backend(module_name):
    """只有构建时依赖缺失才 skip；模块存在后的行为错误仍应正常暴露。"""

    try:
        return importlib.import_module(module_name)
    except ImportError:
        pytest.skip(f"当前 Python 构建未提供 {module_name}")


def test_dumb_backend_uses_documented_dat_and_dir_files(tmp_path):
    """portable backend 把 basename 展开为数据文件和目录索引文件。"""

    path = tmp_path / "portable"
    with dumb.open(str(path), "c") as database:
        database["key"] = "value"

    assert path.with_suffix(".dat").is_file()
    assert path.with_suffix(".dir").is_file()


def test_dumb_backend_exposes_full_mutable_mapping_helpers(tmp_path):
    """纯 Python backend 继承 MutableMapping，提供完整的 mapping helpers。"""

    path = tmp_path / "mapping"
    with dumb.open(str(path), "c") as database:
        database.update({b"one": b"1", b"two": b"2"})

        assert set(database.items()) == {(b"one", b"1"), (b"two", b"2")}
        assert set(database.values()) == {b"1", b"2"}
        assert database.pop(b"one") == b"1"
        assert set(database) == {b"two"}


def test_dumb_sync_flushes_index_and_keeps_database_usable(tmp_path):
    """sync 写回磁盘但不 close；shelve.sync 也会委托给底层数据库的该能力。"""

    path = tmp_path / "synced"
    with dumb.open(str(path), "c") as database:
        database["before"] = "sync"
        returned = database.sync()
        database["after"] = "sync"

        assert returned is None
        assert database["before"] == b"sync"

    with dumb.open(str(path), "r") as reopened:
        assert set(reopened.keys()) == {b"before", b"after"}


def test_dumb_n_mode_discards_old_records(tmp_path):
    """3.5 起 dumb 的 ``n`` 明确总是新建，行为与 generic flag 契约一致。"""

    path = tmp_path / "new"
    with dumb.open(str(path), "c") as database:
        database["old"] = "value"

    with dumb.open(str(path), "n") as database:
        assert not database


@pytest.mark.parametrize("flag", ["r", "w"])
def test_dumb_read_or_write_mode_requires_existing_files(tmp_path, flag):
    """Python 3.8 起 dumb 的 r/w 不再悄悄创建缺失数据库。"""

    path = tmp_path / f"missing-{flag}"

    with pytest.raises(dumb.error):
        dumb.open(str(path), flag)


def test_dumb_read_only_mode_rejects_assignment_and_deletion(tmp_path):
    """3.8 起 ``r`` 真正只读；不能依赖旧版本曾允许 mutation 的历史行为。"""

    path = tmp_path / "readonly"
    with dumb.open(str(path), "c") as database:
        database["key"] = "value"

    with dumb.open(str(path), "r") as database:
        with pytest.raises(dumb.error):
            database["key"] = "changed"
        with pytest.raises(dumb.error):
            del database["key"]


def test_gnu_backend_reports_the_flags_supported_by_this_build():
    """f/s/u 并非每个 gdbm 都接受；先读 open_flags，而不是硬编码构建能力。"""

    gnu = _optional_backend("dbm.gnu")

    assert set("rwc n".replace(" ", "")).issubset(set(gnu.open_flags))
    assert set(gnu.open_flags).issubset(set("rwcnfsu"))


def test_gnu_backend_can_traverse_without_materializing_all_keys(tmp_path):
    """firstkey/nextkey 按内部 hash 顺序遍历，顺序不是 key sort 契约。"""

    gnu = _optional_backend("dbm.gnu")
    path = tmp_path / "gnu-traversal"
    with gnu.open(str(path), "n") as database:
        for key in (b"charlie", b"alpha", b"bravo"):
            database[key] = key.upper()

        traversed = []
        key = database.firstkey()
        while key is not None:
            traversed.append(key)
            key = database.nextkey(key)

        assert set(traversed) == {b"alpha", b"bravo", b"charlie"}
        assert len(traversed) == 3


def test_gnu_backend_specific_maintenance_methods_return_none(tmp_path):
    """sync 强制写盘，reorganize 回收删除空间；两者是 side-effect API。"""

    gnu = _optional_backend("dbm.gnu")
    path = tmp_path / "gnu-maintenance"
    with gnu.open(str(path), "n") as database:
        database[b"temporary"] = b"value"
        del database[b"temporary"]

        assert database.sync() is None
        assert database.reorganize() is None


def test_gnu_mapping_intentionally_omits_items_and_values(tmp_path):
    """gdbm 像 mapping 但不是完整 dict：不要跨 backend 依赖 items()/values()。"""

    gnu = _optional_backend("dbm.gnu")
    path = tmp_path / "gnu-limits"
    with gnu.open(str(path), "n") as database:
        assert not hasattr(database, "items")
        assert not hasattr(database, "values")


def test_ndbm_exposes_the_linked_implementation_name():
    """同一 Python API 可能链接 classic ndbm 或 gdbm compatibility library。"""

    ndbm = _optional_backend("dbm.ndbm")

    assert isinstance(ndbm.library, str)
    assert ndbm.library


def test_ndbm_round_trip_and_limited_mapping_surface(tmp_path):
    """ndbm 保证 bytes mapping/close，但和 gnu 一样不提供 items()/values()。"""

    ndbm = _optional_backend("dbm.ndbm")
    path = tmp_path / "ndbm-records"
    with ndbm.open(str(path), "n") as database:
        database["key"] = "value"

        assert database[b"key"] == b"value"
        assert not hasattr(database, "items")
        assert not hasattr(database, "values")
