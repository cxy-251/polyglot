"""127｜``PyZipFile.writepy`` 编译 Python 模块、包、过滤与 zipimport 工作流。

``PyZipFile`` 在普通 ZIP API 上增加 ``writepy``：它把 ``.py`` 编译为适合从归档导入的
``.pyc``，区分单文件、普通目录和 package 目录，并可用 ``filterfunc`` 跳过整棵子树。
编译优化级别属于归档构建配置；生成物仍是当前解释器版本绑定的 bytecode。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.zipfile.PyZipFile python.zipfile.PyZipFile.optimize
# polyglot-covers: python.zipfile.writepy python.zipfile.writepy-file
# polyglot-covers: python.zipfile.writepy-directory python.zipfile.writepy-package
# polyglot-covers: python.zipfile.writepy-recursion python.zipfile.writepy-sorted
# polyglot-covers: python.zipfile.writepy-filterfunc python.zipfile.filter-subtree
# polyglot-covers: python.zipfile.writepy-path-like python.zipfile.pyc-layout
# polyglot-covers: python.zipfile.bytecode-magic python.zipfile.zipimport-workflow
# polyglot-covers: python.zipfile.writepy-invalid-file python.zipfile.optimized-bytecode

import importlib
import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest


def _write_source(path, source):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _forget_modules(prefix):
    """避免 zipimport 案例把临时模块留给同一 pytest process 的后续测试。"""

    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            sys.modules.pop(name, None)


def test_writepy_compiles_a_single_source_at_the_archive_root(tmp_path):
    """单个 .py 去掉原路径并以 legacy ``module.pyc`` 名称存入根目录。"""

    source = _write_source(tmp_path / "standalone.py", "VALUE = 42\n")
    archive_path = tmp_path / "library.zip"
    with zipfile.PyZipFile(archive_path, "w", optimize=0) as archive:
        archive.writepy(source)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["standalone.pyc"]
        assert archive.read("standalone.pyc").startswith(importlib.util.MAGIC_NUMBER)


def test_writepy_maps_a_non_package_directory_to_top_level_modules(tmp_path):
    """没有 __init__.py 的目录不是 package namespace；其中模块平铺到归档根。"""

    source_dir = tmp_path / "loose_modules"
    _write_source(source_dir / "beta.py", "NAME = 'beta'\n")
    _write_source(source_dir / "alpha.py", "NAME = 'alpha'\n")
    _write_source(source_dir / "ignored.txt", "not Python\n")
    archive_path = tmp_path / "loose.zip"

    with zipfile.PyZipFile(archive_path, "w") as archive:
        archive.writepy(source_dir)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["alpha.pyc", "beta.pyc"]


def test_writepy_preserves_package_layout_and_recurses_in_sorted_order(tmp_path):
    """package/subpackage 依赖 __init__.py 识别；3.7+ 递归目录项按名称排序。"""

    package = tmp_path / "demo_package"
    _write_source(package / "__init__.py", "PACKAGE = True\n")
    _write_source(package / "zeta.py", "VALUE = 'z'\n")
    _write_source(package / "alpha.py", "VALUE = 'a'\n")
    _write_source(package / "nested" / "__init__.py", "NESTED = True\n")
    _write_source(package / "nested" / "module.py", "VALUE = 'nested'\n")
    archive_path = tmp_path / "package.zip"

    with zipfile.PyZipFile(archive_path, "w") as archive:
        archive.writepy(package)

    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()

    assert names == [
        "demo_package/__init__.pyc",
        "demo_package/alpha.pyc",
        "demo_package/zeta.pyc",
        "demo_package/nested/__init__.pyc",
        "demo_package/nested/module.pyc",
    ]


def test_filterfunc_skips_a_file_or_an_entire_directory_subtree(tmp_path):
    """callback 对每个候选 path 调用；目录返回 False 时，不再遍历它的 descendants。"""

    package = tmp_path / "filtered_package"
    _write_source(package / "__init__.py", "PACKAGE = True\n")
    _write_source(package / "core.py", "VALUE = 'core'\n")
    _write_source(package / "test_core.py", "VALUE = 'test'\n")
    _write_source(package / "tests" / "__init__.py", "TESTS = True\n")
    _write_source(package / "tests" / "hidden.py", "HIDDEN = True\n")
    seen = []

    def exclude_tests(path):
        seen.append(path)
        # 官方接口传入 string；显式转 Path 后再按 basename 制定跨平台规则。
        name = Path(path).name
        return name != "tests" and not name.startswith("test_")

    archive_path = tmp_path / "filtered.zip"
    with zipfile.PyZipFile(archive_path, "w") as archive:
        archive.writepy(package, filterfunc=exclude_tests)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == [
            "filtered_package/__init__.pyc",
            "filtered_package/core.pyc",
        ]
    assert str(package / "tests") in seen
    assert str(package / "tests" / "hidden.py") not in seen


def test_compiled_package_can_be_imported_directly_from_the_zip(tmp_path, monkeypatch):
    """PyZipFile 的核心用途是配合 zipimport；归档根加入 sys.path 后可正常导入 package。"""

    package_name = "polyglot_zip_import_demo"
    package = tmp_path / package_name
    _write_source(package / "__init__.py", "from .answer import ANSWER\n")
    _write_source(package / "answer.py", "ANSWER = 6 * 7\n")
    archive_path = tmp_path / "importable.zip"
    with zipfile.PyZipFile(archive_path, "w", optimize=0) as archive:
        archive.writepy(package)

    monkeypatch.syspath_prepend(str(archive_path))
    importlib.invalidate_caches()
    _forget_modules(package_name)
    try:
        imported = importlib.import_module(package_name)
        assert imported.ANSWER == 42
        assert str(archive_path) in imported.__file__
    finally:
        _forget_modules(package_name)


def test_optimize_level_is_applied_when_compiling_bytecode(tmp_path, monkeypatch):
    """optimize=1 会让被编译模块中的 __debug__ 为 False；这是 build-time 语义。"""

    module_name = "polyglot_optimized_zip_module"
    source = _write_source(tmp_path / f"{module_name}.py", "DEBUG = __debug__\n")
    archive_path = tmp_path / "optimized.zip"
    with zipfile.PyZipFile(archive_path, "w", optimize=1) as archive:
        archive.writepy(source)

    monkeypatch.syspath_prepend(str(archive_path))
    importlib.invalidate_caches()
    _forget_modules(module_name)
    try:
        imported = importlib.import_module(module_name)
        assert imported.DEBUG is False
    finally:
        _forget_modules(module_name)


def test_writepy_rejects_a_non_python_file(tmp_path):
    """单文件入口必须以 .py 结尾；目录入口则会自然忽略其他扩展名。"""

    source = _write_source(tmp_path / "notes.txt", "not a module\n")
    with zipfile.PyZipFile(tmp_path / "invalid.zip", "w") as archive:
        with pytest.raises(RuntimeError, match="not a Python file"):
            archive.writepy(source)
