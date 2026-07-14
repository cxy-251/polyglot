"""106｜``dbm.gnu``、``dbm.ndbm`` 与 ``dbm.dumb`` 的能力边界。

GNU/ndbm 依赖 Python 构建时找到的系统库，不能假定所有容器都有；相关测试在模块
不可用时明确 skip。``dbm.dumb`` 是纯 Python 最后备选，格式可移植但不面向高性能或
数据库。三种格式彼此不兼容，业务代码通常应从通用 ``dbm.open`` 进入。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.dbm.gnu python.dbm.gnu.optional python.dbm.gnu.open-flags
# polyglot-covers: python.dbm.gnu.firstkey python.dbm.gnu.nextkey python.dbm.gnu.unsorted
# polyglot-covers: python.dbm.gnu.sync python.dbm.gnu.reorganize python.dbm.gnu.mapping-limits
# polyglot-covers: python.dbm.ndbm python.dbm.ndbm.optional python.dbm.ndbm.library
# polyglot-covers: python.dbm.ndbm.open python.dbm.ndbm.mapping-limits
# polyglot-covers: python.dbm.dumb python.dbm.dumb.portable-fallback python.dbm.dumb.files
# polyglot-covers: python.dbm.dumb.mutable-mapping python.dbm.dumb.sync python.dbm.dumb.flags
# polyglot-covers: python.dbm.backend-incompatibility python.dbm.platform-availability

import importlib

import pytest

from dbm import dumb


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
