"""105｜``dbm`` 的 bytes mapping、后端选择与打开模式。

``dbm`` 是多个不兼容磁盘格式之上的统一入口。它只保存 bytes，不负责 Python
对象序列化；字符串会用默认编码隐式转成 bytes。具体后端取决于 Python 构建环境，所以
案例只依赖文档承诺的交集，不假定文件扩展名或异常的某个具体 subclass。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.dbm.open python.dbm.backend-selection python.dbm.whichdb
# polyglot-covers: python.dbm.bytes-mapping python.dbm.string-coercion python.dbm.default-encoding
# polyglot-covers: python.dbm.keys python.dbm.contains python.dbm.get python.dbm.setdefault
# polyglot-covers: python.dbm.delete python.dbm.KeyError python.dbm.type-restriction
# polyglot-covers: python.dbm.flag-r python.dbm.flag-w python.dbm.flag-c python.dbm.flag-n
# polyglot-covers: python.dbm.read-only python.dbm.missing-database python.dbm.persistence
# polyglot-covers: python.dbm.context-manager python.dbm.close python.dbm.error-tuple
# polyglot-covers: python.dbm.backend-file-format python.dbm.not-object-serialization

import dbm

import pytest


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
