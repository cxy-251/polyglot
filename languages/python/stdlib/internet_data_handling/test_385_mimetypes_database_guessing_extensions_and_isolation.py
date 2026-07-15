"""385｜从文件名/URL 猜 MIME type 与 Content-Encoding。

guess_type 只看名称后缀，不读取文件内容；返回的 encoding 是 gzip/compress 等
Content-Encoding，不是 MIME Content-Transfer-Encoding。encoding suffix 大小写敏感，type suffix
才会回退到不区分大小写。suffix_map 可先把 .tgz 这类复合简写展开，再分别识别 type 与 encoding。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mimetypes.guess_type
# polyglot-covers: python.mimetypes.guess-type-pathlike
# polyglot-covers: python.mimetypes.guess-type-url
# polyglot-covers: python.mimetypes.guess-type-unknown-none
# polyglot-covers: python.mimetypes.guess-type-does-not-inspect-content
# polyglot-covers: python.mimetypes.guess-type-type-and-encoding-tuple
# polyglot-covers: python.mimetypes.encoding-is-content-encoding
# polyglot-covers: python.mimetypes.encoding-suffix-case-sensitive
# polyglot-covers: python.mimetypes.type-suffix-case-insensitive-fallback
# polyglot-covers: python.mimetypes.suffix_map
# polyglot-covers: python.mimetypes.encodings_map
# polyglot-covers: python.mimetypes.compound-suffix-expansion



import mimetypes
from pathlib import Path
import io

def test_common_filename_path_and_url_suffixes_are_recognized_without_file_io():
    assert mimetypes.guess_type("document.txt") == ("text/plain", None)
    assert mimetypes.guess_type(Path("missing.json")) == ("application/json", None)
    assert mimetypes.guess_type("https://example.invalid/image.png") == (
        "image/png",
        None,
    )
    assert mimetypes.guess_type("no-known-suffix.polyglot-unknown") == (None, None)


def test_isolated_database_separates_type_suffix_from_case_sensitive_encoding():
    database = mimetypes.MimeTypes()
    database.add_type("application/x-package", ".pkg")
    database.encodings_map[".zz"] = "demo-compression"
    database.suffix_map[".bundle"] = ".pkg.zz"

    assert database.guess_type("artifact.pkg.zz") == (
        "application/x-package",
        "demo-compression",
    )
    assert database.guess_type("artifact.PKG.zz") == (
        "application/x-package",
        "demo-compression",
    )
    assert database.guess_type("artifact.pkg.ZZ") == (None, None)
    assert database.guess_type("artifact.bundle") == (
        "application/x-package",
        "demo-compression",
    )


def test_builtin_tgz_mapping_reports_archive_type_and_transport_encoding():
    database = mimetypes.MimeTypes()
    assert database.suffix_map[".tgz"] == ".tar.gz"
    assert database.encodings_map[".gz"] == "gzip"
    assert database.guess_type("backup.tgz") == ("application/x-tar", "gzip")


# 386｜MimeTypes 独立数据库、strict 分区与 mime.types 文件。
#
# MimeTypes 复制模块默认表，适合每个租户/协议维护独立扩展，不污染进程全局。strict=True 查询官方
# 表，False 还包含 common/non-standard 表；add_type 可替换 extension 的旧 type，并同步反向索引。
# mime.types 每行先写 type，后写一个或多个不带点的 extension，后加载的文件具有更高优先级。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.mimetypes.MimeTypes
# polyglot-covers: python.mimetypes.MimeTypes-independent-database
# polyglot-covers: python.mimetypes.MimeTypes.add_type
# polyglot-covers: python.mimetypes.strict-standard-versus-common
# polyglot-covers: python.mimetypes.add-type-replaces-extension
# polyglot-covers: python.mimetypes.MimeTypes.guess_type
# polyglot-covers: python.mimetypes.MimeTypes.guess_extension
# polyglot-covers: python.mimetypes.MimeTypes.guess_all_extensions
# polyglot-covers: python.mimetypes.MimeTypes.read
# polyglot-covers: python.mimetypes.MimeTypes.readfp
# polyglot-covers: python.mimetypes.MimeTypes-filenames-overlay
# polyglot-covers: python.mimetypes.mime-types-file-later-entry-wins
# polyglot-covers: python.mimetypes.read_mime_types
# polyglot-covers: python.mimetypes.read-mime-types-missing-none



def test_standard_and_nonstandard_mappings_have_distinct_strict_visibility():
    database = mimetypes.MimeTypes()
    database.add_type("application/x-official-demo", ".demo", strict=True)
    database.add_type("application/x-common-demo", ".common", strict=False)

    assert database.guess_type("file.demo", strict=True)[0] == "application/x-official-demo"
    assert database.guess_type("file.common", strict=True) == (None, None)
    assert database.guess_type("file.common", strict=False)[0] == "application/x-common-demo"
    assert database.guess_extension("application/x-common-demo", strict=True) is None
    assert database.guess_extension("application/x-common-demo", strict=False) == ".common"
    assert database.guess_all_extensions("application/x-official-demo") == [".demo"]


def test_readfp_and_read_overlay_entries_and_keep_reverse_index_in_sync(tmp_path):
    database = mimetypes.MimeTypes()
    database.readfp(io.StringIO("application/x-one one uno\n"))
    assert set(database.guess_all_extensions("application/x-one")) == {".one", ".uno"}

    type_file = tmp_path / "mime.types"
    type_file.write_text(
        "application/x-first shared first\napplication/x-second shared second\n",
        encoding="utf-8",
    )
    database.read(str(type_file))
    assert database.guess_type("file.shared")[0] == "application/x-second"
    assert database.guess_type("file.first")[0] == "application/x-first"
    assert database.guess_type("file.second")[0] == "application/x-second"


def test_constructor_and_standalone_reader_load_a_type_file(tmp_path):
    type_file = tmp_path / "custom.types"
    type_file.write_text("application/x-polyglot pgl poly\n", encoding="utf-8")

    database = mimetypes.MimeTypes(filenames=[str(type_file)])
    assert database.guess_type("lesson.pgl")[0] == "application/x-polyglot"
    loaded = mimetypes.read_mime_types(str(type_file))
    assert loaded[".pgl"] == "application/x-polyglot"
    assert loaded[".poly"] == "application/x-polyglot"
    assert mimetypes.read_mime_types(str(tmp_path / "missing.types")) is None


# 387｜模块全局表的 init/add_type，以及测试隔离。
#
# 模块 convenience functions 共用可变全局数据库：首次查询会惰性 init，add_type 会影响后续所有
# 调用。init(files=[]) 只装载内建 well-known 表，避免宿主系统 mime.types；init(None) 则完全重建
# 并读取 knownfiles。库代码若不想产生跨测试/租户状态泄漏，应优先持有独立 MimeTypes 实例。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.mimetypes.init
# polyglot-covers: python.mimetypes.init-empty-files-builtins-only
# polyglot-covers: python.mimetypes.init-none-rebuilds-defaults
# polyglot-covers: python.mimetypes.repeated-init-allowed
# polyglot-covers: python.mimetypes.inited
# polyglot-covers: python.mimetypes.knownfiles
# polyglot-covers: python.mimetypes.types_map
# polyglot-covers: python.mimetypes.common_types
# polyglot-covers: python.mimetypes.add_type
# polyglot-covers: python.mimetypes.global-add-type-process-wide-state
# polyglot-covers: python.mimetypes.prefer-instance-for-state-isolation



def _preserve_global_database_for_monkeypatch(monkeypatch):
    # 先让 monkeypatch 记录原对象；即使 init 随后替换模块属性，teardown 仍会恢复原引用。
    for name in (
        "_db",
        "inited",
        "suffix_map",
        "encodings_map",
        "types_map",
        "common_types",
    ):
        monkeypatch.setattr(mimetypes, name, getattr(mimetypes, name))


def test_init_with_empty_file_list_is_repeatable_and_uses_builtin_tables(monkeypatch):
    _preserve_global_database_for_monkeypatch(monkeypatch)
    monkeypatch.setattr(mimetypes, "knownfiles", [])

    mimetypes.init(files=[])
    first = mimetypes.guess_type("lesson.html")
    first_size = len(mimetypes.types_map)
    # files=None 完全重建默认状态；knownfiles 已隔离为空，所以不会读取宿主机配置。
    mimetypes.init(files=None)
    assert mimetypes.inited is True
    assert mimetypes.guess_type("lesson.html") == first == ("text/html", None)
    assert len(mimetypes.types_map) == first_size
    assert isinstance(mimetypes.knownfiles, list)
    assert isinstance(mimetypes.common_types, dict)


def test_module_add_type_mutates_the_shared_database_but_is_isolated_here(monkeypatch):
    isolated = mimetypes.MimeTypes()
    monkeypatch.setattr(mimetypes, "_db", isolated)
    monkeypatch.setattr(mimetypes, "inited", True)
    monkeypatch.setattr(mimetypes, "suffix_map", isolated.suffix_map)
    monkeypatch.setattr(mimetypes, "encodings_map", isolated.encodings_map)
    monkeypatch.setattr(mimetypes, "types_map", isolated.types_map[1])
    monkeypatch.setattr(mimetypes, "common_types", isolated.types_map[0])

    assert mimetypes.guess_type("lesson.pglobal") == (None, None)
    assert mimetypes.add_type("application/x-global-demo", ".pglobal") is None
    assert mimetypes.guess_type("lesson.pglobal")[0] == "application/x-global-demo"
    assert mimetypes.guess_extension("application/x-global-demo") == ".pglobal"
