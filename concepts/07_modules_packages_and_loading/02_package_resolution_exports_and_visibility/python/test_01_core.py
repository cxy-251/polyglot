"""包解析、导出与可见性。

共同问题：包名如何解析到文件；包入口如何组织公共 API；私有名称是否强制隐藏；
相对导入以什么为基准。
"""

# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/python/language/test_018_imports_modules_and_packages.py

import importlib
import importlib.util
import sys

import pytest


def make_package(tmp_path):
    package = tmp_path / "demo"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from .core import public\n__all__ = ['public']\n",
        encoding="utf-8",
    )
    (package / "core.py").write_text(
        "from .sibling import sibling\npublic = 1\n_private = 2\n",
        encoding="utf-8",
    )
    (package / "sibling.py").write_text("sibling = 3\n", encoding="utf-8")


def clear_package():
    for name in ["demo", "demo.core", "demo.sibling"]:
        sys.modules.pop(name, None)


@pytest.fixture
def clean_demo_package():
    clear_package()
    yield
    clear_package()


def test_package_name_resolves_through_sys_path(tmp_path, monkeypatch, clean_demo_package):
    make_package(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    spec = importlib.util.find_spec("demo")

    assert spec is not None
    assert spec.submodule_search_locations is not None


def test_package_init_can_reexport_a_public_api(tmp_path, monkeypatch, clean_demo_package):
    make_package(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    package = importlib.import_module("demo")

    assert package.public == 1
    assert package.__all__ == ["public"]


def test_relative_import_uses_the_containing_package(tmp_path, monkeypatch, clean_demo_package):
    make_package(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    core = importlib.import_module("demo.core")

    assert core.__package__ == "demo"
    assert core.public == 1
    assert core.sibling == 3


def test_underscore_is_a_visibility_convention_not_access_control(
    tmp_path,
    monkeypatch,
    clean_demo_package,
):
    make_package(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    core = importlib.import_module("demo.core")

    assert core._private == 2
