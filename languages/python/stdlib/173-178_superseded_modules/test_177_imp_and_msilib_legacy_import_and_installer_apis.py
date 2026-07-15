"""177｜imp 与 msilib：旧式导入接口和 Windows Installer 数据库构建。

imp 是 importlib 出现前的底层导入门面；msilib 是仅 Windows 提供的 MSI
数据库构建包。案例展示遗留调用的资源和 sys.modules 语义，也展示
可在临时目录完成的 MSI 表、Record 与 CAB 元数据工作流。新代码应改用
importlib；安装器项目则应先评估仍在维护的专用工具链。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.imp python.imp.new-module python.imp.sys-modules
# polyglot-covers: python.imp.get-magic python.imp.get-tag python.imp.cache-paths
# polyglot-covers: python.imp.get-suffixes python.imp.find-module
# polyglot-covers: python.imp.load-module python.imp.source-file-lifetime
# polyglot-covers: python.imp.package-directory python.imp.builtin-module
# polyglot-covers: python.imp.import-lock python.imp.null-importer
# polyglot-covers: python.stdlib.msilib python.msilib.windows-only
# polyglot-covers: python.msilib.make-id python.msilib.gen-uuid python.msilib.binary
# polyglot-covers: python.msilib.table python.msilib.change-sequence
# polyglot-covers: python.msilib.cab python.msilib.create-record
# polyglot-covers: python.msilib.open-database python.msilib.add-data
# polyglot-covers: python.msilib.schema python.msilib.sequence python.msilib.text

import gc
import importlib.machinery
import importlib.util
import imp
import os
import re
import sys

import pytest


def windows_msilib():
    if os.name != "nt":
        pytest.skip("msilib 只在 Windows 解释器构建中提供")
    return pytest.importorskip("msilib")


def test_imp_new_module_creates_metadata_but_does_not_register_the_module():
    name = "_polyglot_imp_177_new"
    sys.modules.pop(name, None)

    module = imp.new_module(name)

    assert module.__name__ == name
    assert module.__doc__ is None
    assert module.__loader__ is None
    assert name not in sys.modules
    # 只有成功加载或显式赋值才会进入 sys.modules；
    # 创建对象不等于可被 import。


def test_imp_magic_tag_and_cache_paths_delegate_to_importlib(tmp_path):
    source = tmp_path / "lesson.py"

    assert imp.get_magic() == importlib.util.MAGIC_NUMBER
    assert imp.get_tag() == sys.implementation.cache_tag
    assert imp.cache_from_source(str(source)) == importlib.util.cache_from_source(
        str(source)
    )

    cache = imp.cache_from_source(str(source), debug_override=False)
    assert imp.source_from_cache(cache) == str(source)
    # 路径计算不要求源文件真实存在；debug_override 是旧式优化标签入口。


def test_get_suffixes_labels_extension_source_and_bytecode_loader_inputs():
    suffixes = imp.get_suffixes()

    assert all(len(item) == 3 for item in suffixes)
    assert any(
        suffix in importlib.machinery.SOURCE_SUFFIXES
        and mode == "r"
        and kind == imp.PY_SOURCE
        for suffix, mode, kind in suffixes
    )
    assert any(
        suffix in importlib.machinery.BYTECODE_SUFFIXES
        and mode == "rb"
        and kind == imp.PY_COMPILED
        for suffix, mode, kind in suffixes
    )
    if importlib.machinery.EXTENSION_SUFFIXES:
        assert any(kind == imp.C_EXTENSION for _, _, kind in suffixes)


def test_find_and_load_module_requires_closing_the_returned_source_file(tmp_path):
    source = tmp_path / "legacy_lesson.py"
    source.write_text("answer = 42\n", encoding="utf-8")
    module_name = "_polyglot_imp_177_source"
    sys.modules.pop(module_name, None)

    file_object, pathname, details = imp.find_module(
        "legacy_lesson",
        [str(tmp_path)],
    )
    try:
        assert pathname == str(source)
        assert details == (".py", "r", imp.PY_SOURCE)
        module = imp.load_module(module_name, file_object, pathname, details)
        assert module.answer == 42
        assert module.__file__ == str(source)
        assert sys.modules[module_name] is module
    finally:
        if file_object is not None and not file_object.closed:
            file_object.close()
        sys.modules.pop(module_name, None)

    # find_module 返回的文件由调用者负责关闭；
    # 某些 load 路径虽会先关闭，也不能依赖。


def test_find_module_returns_a_directory_descriptor_for_packages(tmp_path):
    package = tmp_path / "legacy_package"
    package.mkdir()
    (package / "__init__.py").write_text("kind = 'package'\n", encoding="utf-8")
    module_name = "_polyglot_imp_177_package"
    sys.modules.pop(module_name, None)

    file_object, pathname, details = imp.find_module(
        "legacy_package",
        [str(tmp_path)],
    )
    try:
        assert file_object is None
        assert pathname == str(package)
        assert details == ("", "", imp.PKG_DIRECTORY)
        module = imp.load_module(module_name, file_object, pathname, details)
        assert module.kind == "package"
        assert module.__path__ == [str(package)]
    finally:
        sys.modules.pop(module_name, None)


def test_find_module_recognizes_builtins_without_opening_a_file():
    file_object, pathname, details = imp.find_module("sys")

    assert file_object is None
    assert pathname is None
    assert details == ("", "", imp.C_BUILTIN)
    assert imp.load_module("sys", file_object, pathname, details) is sys


def test_find_module_rejects_dotted_names_and_missing_modules(tmp_path):
    with pytest.raises(ImportError):
        imp.find_module("package.child", [str(tmp_path)])
    with pytest.raises(ImportError) as raised:
        imp.find_module("definitely_missing", [str(tmp_path)])
    assert raised.value.name == "definitely_missing"
    # 子模块应先取得父包 __path__，再只把 child 交给 find_module。


def test_imp_import_lock_is_reentrant_and_must_be_released_symmetrically():
    imp.acquire_lock()
    imp.acquire_lock()
    try:
        assert imp.lock_held() is True
    finally:
        imp.release_lock()
        imp.release_lock()

    assert imp.lock_held() is False
    # 遗漏一次 release 会阻塞其他线程的导入；
    # 现代代码通常不应直接管理全局导入锁。


def test_null_importer_accepts_non_directories_but_never_finds_a_module(tmp_path):
    missing_path = tmp_path / "not-created"
    importer = imp.NullImporter(str(missing_path))

    assert importer.find_module("anything") is None
    with pytest.raises(ImportError, match="empty pathname"):
        imp.NullImporter("")
    with pytest.raises(ImportError, match="existing directory"):
        imp.NullImporter(str(tmp_path))


def test_msilib_identifiers_uuid_and_binary_wrapper_are_msi_shaped():
    msilib = windows_msilib()

    assert msilib.make_id("123 bad-name.txt") == "_123_bad_name.txt"
    assert msilib.make_id("already.Valid_7") == "already.Valid_7"
    assert re.fullmatch(
        r"\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}",
        msilib.gen_uuid(),
    )

    binary = msilib.Binary("payload.bin")
    assert binary.name == "payload.bin"
    assert repr(binary) == 'msilib.Binary(os.path.join(dirname,"payload.bin"))'


def test_msilib_table_translates_field_bitmasks_into_msi_sql():
    msilib = windows_msilib()
    table = msilib.Table("Demo")
    table.add_field(
        1,
        "Name",
        msilib.type_string | 32 | msilib.type_key,
    )
    table.add_field(
        2,
        "Count",
        msilib.type_long | 4 | msilib.type_nullable,
    )

    sql = table.sql()

    assert sql.startswith("CREATE TABLE Demo (")
    assert "`Name` CHAR(32) NOT NULL" in sql
    assert "`Count` LONG" in sql
    assert sql.endswith("PRIMARY KEY `Name`)")


def test_change_sequence_preserves_unspecified_fields_and_rejects_unknown_actions():
    msilib = windows_msilib()
    actions = [
        ("Prepare", "READY", 100),
        ("Install", None, 200),
    ]

    msilib.change_sequence(actions, "Prepare", seqno=150)
    msilib.change_sequence(actions, "Install", cond="ENABLED")

    assert actions == [
        ("Prepare", "READY", 150),
        ("Install", "ENABLED", 200),
    ]
    with pytest.raises(ValueError, match="Action not found"):
        msilib.change_sequence(actions, "Missing", seqno=300)


def test_cab_assigns_stable_unique_logical_ids_and_ignores_directories(tmp_path):
    msilib = windows_msilib()
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    cab = msilib.CAB("archive.cab")

    first_result = cab.append(str(first), "bad name.bin", None)
    second_result = cab.append(str(second), "bad name.bin", None)

    assert first_result == (1, "bad_name.bin")
    assert second_result == (2, "bad_name.bin.1")
    assert cab.append(str(tmp_path), "ignored", None) is None
    assert cab.files == [
        (str(first), "bad_name.bin"),
        (str(second), "bad_name.bin.1"),
    ]
    # CAB.append 只收集清单；commit 才压缩并把流写入 MSI 数据库。


def test_create_record_has_one_based_typed_fields_and_clear_data():
    msilib = windows_msilib()
    record = msilib.CreateRecord(2)

    record.SetString(1, "lesson")
    record.SetInteger(2, 177)
    assert record.GetFieldCount() == 2
    assert record.GetString(1) == "lesson"
    assert record.GetInteger(2) == 177

    record.ClearData()
    assert record.GetString(1) == ""
    assert record.GetInteger(2) == msilib.MSI_NULL_INTEGER
    # MSI Record 字段从 1 开始；字段 0 另有格式字符串含义，
    # 不能按 Python 序列理解。


def test_open_database_table_and_add_data_round_trip_in_a_temporary_msi(tmp_path):
    msilib = windows_msilib()
    database_path = tmp_path / "lesson.msi"
    database = msilib.OpenDatabase(
        str(database_path),
        msilib.MSIDBOPEN_CREATE,
    )
    table = msilib.Table("Demo")
    table.add_field(1, "Name", msilib.type_string | 32 | msilib.type_key)
    table.add_field(2, "Count", msilib.type_long | 4)
    table.create(database)
    msilib.add_data(database, "Demo", [("lesson", 177)])
    database.Commit()

    view = database.OpenView("SELECT `Name`, `Count` FROM `Demo`")
    view.Execute(None)
    record = view.Fetch()
    assert record.GetString(1) == "lesson"
    assert record.GetInteger(2) == 177
    assert view.Fetch() is None
    view.Close()

    del record, view, database
    gc.collect()
    assert database_path.is_file()


def test_msilib_package_supplies_standard_schema_sequences_and_ui_text():
    msilib = windows_msilib()
    schema = pytest.importorskip("msilib.schema")
    sequence = pytest.importorskip("msilib.sequence")
    text = pytest.importorskip("msilib.text")

    table_names = {table.name for table in schema.tables}
    assert {"Property", "Directory", "Component", "File", "Media"} <= table_names
    assert any(
        action == "InstallFiles" and number == 4000
        for action, condition, number in sequence.InstallExecuteSequence
    )
    assert any(
        action == "InstallFiles" and "Copying" in description
        for action, description, template in text.ActionText
    )
    # schema 描述 MSI 表，sequence 描述动作顺序，text 提供默认界面文案；
    # add_tables 可把这些 Python 数据批量写入刚创建的数据库。
