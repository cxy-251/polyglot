"""386｜MimeTypes 独立数据库、strict 分区与 mime.types 文件。

MimeTypes 复制模块默认表，适合每个租户/协议维护独立扩展，不污染进程全局。strict=True 查询官方
表，False 还包含 common/non-standard 表；add_type 可替换 extension 的旧 type，并同步反向索引。
mime.types 每行先写 type，后写一个或多个不带点的 extension，后加载的文件具有更高优先级。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import io
import mimetypes


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
