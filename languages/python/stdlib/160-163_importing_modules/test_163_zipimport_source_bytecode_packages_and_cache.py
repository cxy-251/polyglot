"""163｜zipimport：归档中的源码、字节码、package 和 importer 缓存。

把 ZIP 路径放入 ``sys.path`` 后，普通 import 会自动使用 ``zipimporter``；归档
可以保存 ``.py/.pyc``、package 和数据，但不能原地生成缓存或加载动态扩展。
本套同时从普通 import 与 importer 协议两侧，观察查找、源码、
代码对象、数据、
子目录前缀、3.10 新增方法及缓存失效。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.zipimport python.zipimport.automatic-path-hook
# polyglot-covers: python.zipimport.zipimporter python.zipimport.invalid-archive
# polyglot-covers: python.zipimport.archive-prefix python.zipimport.subdirectory-path
# polyglot-covers: python.zipimport.find-spec-3.10
# polyglot-covers: python.zipimport.create-module-3.10
# polyglot-covers: python.zipimport.exec-module-3.10
# polyglot-covers: python.zipimport.find-module python.zipimport.find-loader
# polyglot-covers: python.zipimport.legacy-methods-deprecated-3.10
# polyglot-covers: python.zipimport.get-code python.zipimport.get-source
# polyglot-covers: python.zipimport.get-filename python.zipimport.is-package
# polyglot-covers: python.zipimport.get-data
# polyglot-covers: python.zipimport.module-and-package-import
# polyglot-covers: python.zipimport.relative-package-import
# polyglot-covers: python.zipimport.pyc-only-module
# polyglot-covers: python.zipimport.no-pyc-writeback
# polyglot-covers: python.zipimport.dynamic-extension-disallowed
# polyglot-covers: python.zipimport.archive-comment-3.8
# polyglot-covers: python.zipimport.invalidate-caches-3.10
# polyglot-covers: python.zipimport.path-importer-cache
# polyglot-covers: python.zipimport.pkgutil-iter-modules
# polyglot-covers: python.zipimport.run-path-main
# polyglot-covers: python.zipimport.zip-import-error

from contextlib import contextmanager
import importlib
from importlib import machinery
from importlib import util
import marshal
from pathlib import Path
import pkgutil
import runpy
import struct
import sys
import zipfile
import zipimport

import pytest


@contextmanager
def clean_zip_modules(*prefixes):
    existing = set(sys.modules)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name in existing:
                continue
            if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
                sys.modules.pop(name, None)


def timestamp_pyc(source, filename):
    """构造无对应源码也可加载的时间戳 pyc（16 字节头 + marshal code）。"""

    source_bytes = source.encode("utf-8")
    code_object = compile(source, filename, "exec")
    header = util.MAGIC_NUMBER + struct.pack("<III", 0, 0, len(source_bytes))
    return header + marshal.dumps(code_object)


def build_archive(path, *, include_main=False):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = b"Python 3.8+ zipimport accepts archive comments"
        archive.writestr(
            "polyglot_zip_module.py",
            "VALUE = 42\n",
        )
        archive.writestr(
            "polyglot_zip_package/__init__.py",
            "from .helper import helper_value\n"
            "PACKAGE_VALUE = helper_value + 1\n",
        )
        archive.writestr(
            "polyglot_zip_package/helper.py",
            "helper_value = 41\n",
        )
        archive.writestr("polyglot_zip_package/data.bin", b"zip-data")
        archive.writestr("library/prefixed_module.py", "VALUE = 'prefixed'\n")
        archive.writestr(
            "compiled_only.pyc",
            timestamp_pyc("VALUE = 'bytecode only'\n", f"{path}/compiled_only.py"),
        )
        extension_name = "fake_native" + machinery.EXTENSION_SUFFIXES[0]
        archive.writestr(extension_name, b"not a real extension")
        archive.writestr("notes.txt", "not importable\n")
        if include_main:
            archive.writestr(
                "__main__.py",
                "import sys\n"
                "RESULT = 42\n"
                "OBSERVED = (__name__, __spec__.name, sys.argv[0])\n",
            )
    return path


def test_zipimport_error_is_import_error_and_invalid_archive_is_rejected(tmp_path):
    invalid = tmp_path / "not-an-archive.zip"
    invalid.write_text("plain text", encoding="utf-8")

    assert issubclass(zipimport.ZipImportError, ImportError)
    with pytest.raises(zipimport.ZipImportError):
        zipimport.zipimporter(str(invalid))
    with pytest.raises(zipimport.ZipImportError):
        zipimport.zipimporter(str(tmp_path / "missing.zip"))


def test_zipimporter_archive_and_prefix_describe_root_or_subdirectory(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    root_importer = zipimport.zipimporter(str(archive))
    prefixed_importer = zipimport.zipimporter(f"{archive}/library")

    assert Path(root_importer.archive) == archive
    assert root_importer.prefix == ""
    assert Path(prefixed_importer.archive) == archive
    assert prefixed_importer.prefix == "library/"
    assert prefixed_importer.find_spec("prefixed_module") is not None
    assert root_importer.find_spec("prefixed_module") is None


def test_find_spec_reports_module_and_package_metadata_in_python_310(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))
    module_spec = importer.find_spec("polyglot_zip_module")
    package_spec = importer.find_spec("polyglot_zip_package")

    assert module_spec.name == "polyglot_zip_module"
    assert module_spec.loader is importer
    assert module_spec.origin.endswith("modules.zip/polyglot_zip_module.py")
    assert module_spec.submodule_search_locations is None

    assert package_spec.name == "polyglot_zip_package"
    assert package_spec.loader is importer
    assert package_spec.origin.endswith("modules.zip/polyglot_zip_package/__init__.py")
    assert len(package_spec.submodule_search_locations) == 1
    assert package_spec.submodule_search_locations[0].endswith(
        "modules.zip/polyglot_zip_package"
    )
    assert importer.find_spec("missing_zip_module") is None


def test_create_module_and_exec_module_follow_modern_loader_protocol(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))
    spec = importer.find_spec("polyglot_zip_module")

    assert importer.create_module(spec) is None
    module = util.module_from_spec(spec)
    importer.exec_module(module)
    assert module.VALUE == 42
    assert module.__spec__ is spec
    assert module.__loader__ is importer
    assert "polyglot_zip_module" not in sys.modules


@pytest.mark.filterwarnings("ignore:zipimporter.find_loader")
def test_legacy_find_methods_still_delegate_but_are_deprecated_in_310(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))

    with pytest.warns(DeprecationWarning, match="find_module"):
        assert importer.find_module("polyglot_zip_module") is importer
        assert importer.find_module("missing_zip_module") is None
    # find_loader 的 C 实现一次调用会重复发出同一弃用警告；本用例已通过
    # find_module 显式断言旧协议会告警，故对重复噪声使用精确过滤器。
    loader, portions = importer.find_loader("polyglot_zip_module")
    assert loader is importer
    assert portions == []
    # 新代码使用 find_spec + exec_module；find_module/find_loader/load_module
    # 只为旧 PEP 302 调用者保留。


def test_get_source_code_filename_and_package_status(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))

    source = importer.get_source("polyglot_zip_module")
    code_object = importer.get_code("polyglot_zip_module")
    filename = importer.get_filename("polyglot_zip_module")

    assert source == "VALUE = 42\n"
    assert code_object.co_filename == filename
    assert filename.endswith("modules.zip/polyglot_zip_module.py")
    assert importer.is_package("polyglot_zip_module") is False
    assert importer.is_package("polyglot_zip_package") is True


def test_missing_module_queries_raise_zip_import_error_where_documented(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))

    for query in (
        importer.get_code,
        importer.get_filename,
        importer.get_source,
        importer.is_package,
    ):
        with pytest.raises(zipimport.ZipImportError):
            query("missing_zip_module")


def test_get_data_reads_arbitrary_archive_member_but_missing_path_raises_oserror(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))
    resource_path = f"{archive}/polyglot_zip_package/data.bin"

    assert importer.get_data(resource_path) == b"zip-data"
    with pytest.raises(OSError):
        importer.get_data(f"{archive}/missing.bin")


def test_normal_import_automatically_uses_zip_path_hook_for_module_and_package(
    tmp_path,
    monkeypatch,
):
    archive = build_archive(tmp_path / "modules.zip")
    monkeypatch.syspath_prepend(archive)

    with clean_zip_modules("polyglot_zip_module", "polyglot_zip_package"):
        module = importlib.import_module("polyglot_zip_module")
        package = importlib.import_module("polyglot_zip_package")
        helper = importlib.import_module("polyglot_zip_package.helper")

        assert module.VALUE == 42
        assert package.PACKAGE_VALUE == 42
        assert helper.helper_value == 41
        assert isinstance(module.__loader__, zipimport.zipimporter)
        assert isinstance(package.__loader__, zipimport.zipimporter)
        assert module.__file__.endswith("modules.zip/polyglot_zip_module.py")
        assert package.__path__[0].endswith("modules.zip/polyglot_zip_package")


def test_archive_subdirectory_can_be_a_sys_path_entry(tmp_path, monkeypatch):
    archive = build_archive(tmp_path / "modules.zip")
    monkeypatch.syspath_prepend(f"{archive}/library")

    with clean_zip_modules("prefixed_module"):
        module = importlib.import_module("prefixed_module")
        assert module.VALUE == "prefixed"
        assert module.__loader__.prefix == "library/"
        assert module.__file__.endswith("modules.zip/library/prefixed_module.py")


def test_pyc_only_module_has_code_but_no_source_and_imports_normally(tmp_path, monkeypatch):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))

    assert importer.get_source("compiled_only") is None
    code_object = importer.get_code("compiled_only")
    assert code_object.co_filename.endswith("modules.zip/compiled_only.py")

    monkeypatch.syspath_prepend(archive)
    with clean_zip_modules("compiled_only"):
        module = importlib.import_module("compiled_only")
        assert module.VALUE == "bytecode only"
        assert module.__file__.endswith("modules.zip/compiled_only.pyc")


def test_source_import_does_not_write_pyc_back_into_archive(tmp_path, monkeypatch):
    archive = build_archive(tmp_path / "modules.zip")
    with zipfile.ZipFile(archive) as bundle:
        before = set(bundle.namelist())

    monkeypatch.syspath_prepend(archive)
    with clean_zip_modules("polyglot_zip_module"):
        importlib.import_module("polyglot_zip_module")

    with zipfile.ZipFile(archive) as bundle:
        after = set(bundle.namelist())
    assert after == before
    assert "__pycache__" not in "\n".join(after)


def test_dynamic_extension_member_and_unrecognized_files_are_not_importable(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))

    assert importer.find_spec("fake_native") is None
    assert importer.find_spec("notes") is None
    # zipimport 只装载 py/pyc；动态库需要操作系统 loader 和真实文件路径。


def test_archives_with_comments_are_importable_since_python_38(tmp_path):
    archive = build_archive(tmp_path / "commented.zip")
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.comment

    importer = zipimport.zipimporter(str(archive))
    assert importer.find_spec("polyglot_zip_module") is not None


def test_invalidate_caches_notices_members_added_after_importer_creation(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    importer = zipimport.zipimporter(str(archive))
    assert importer.find_spec("added_later") is None

    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("added_later.py", "VALUE = 'new'\n")

    importer.invalidate_caches()
    spec = importer.find_spec("added_later")
    assert spec is not None
    module = util.module_from_spec(spec)
    importer.exec_module(module)
    assert module.VALUE == "new"


def test_path_importer_cache_stores_zipimporter_for_archive_entry(tmp_path, monkeypatch):
    archive = build_archive(tmp_path / "modules.zip")
    path_entry = str(archive)
    monkeypatch.setattr(sys, "path_importer_cache", sys.path_importer_cache.copy())
    monkeypatch.syspath_prepend(path_entry)
    sys.path_importer_cache.pop(path_entry, None)

    with clean_zip_modules("polyglot_zip_module"):
        importlib.import_module("polyglot_zip_module")
        assert isinstance(sys.path_importer_cache[path_entry], zipimport.zipimporter)


def test_pkgutil_iter_modules_uses_zipimporter_nonstandard_enumeration_support(tmp_path):
    archive = build_archive(tmp_path / "modules.zip")
    found = {
        information.name: information
        for information in pkgutil.iter_modules([str(archive)])
    }

    assert found["polyglot_zip_module"].ispkg is False
    assert found["polyglot_zip_package"].ispkg is True
    assert found["compiled_only"].ispkg is False
    assert "notes" not in found
    assert found["fake_native"].ispkg is False
    # pkgutil 只按文件后缀枚举，所以会报告归档里的动态扩展；
    # zipimport 实际不能加载它，“可发现”不等于“可导入”。


def test_run_path_executes_archive_main_and_restores_process_state(tmp_path):
    archive = build_archive(tmp_path / "application.zip", include_main=True)
    original_path = sys.path.copy()
    original_argv0 = sys.argv[0]

    result = runpy.run_path(str(archive), run_name="zip_cli")
    assert result["RESULT"] == 42
    observed_name, observed_spec, observed_argv0 = result["OBSERVED"]
    assert observed_name == "zip_cli"
    assert observed_spec == "__main__"
    assert Path(observed_argv0) == archive
    assert isinstance(result["__loader__"], zipimport.zipimporter)
    assert sys.path == original_path
    assert sys.argv[0] == original_argv0
