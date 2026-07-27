"""模块、导入、链接与绑定可见性。

共同问题：模块何时执行；导入得到模块还是值快照；命名空间如何隔离；
声明如何跨文件暴露。
"""

# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/python/language/test_018_imports_modules_and_packages.py

import importlib
import sys

import pytest


@pytest.fixture
def imported_names():
    names = []
    yield names
    for name in names:
        sys.modules.pop(name, None)


def test_import_executes_module_and_returns_its_namespace(tmp_path, monkeypatch, imported_names):
    (tmp_path / "sample.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.append("sample")

    module = importlib.import_module("sample")

    assert module.value == 1
    assert module.__name__ == "sample"


def test_module_attribute_is_live_but_from_import_binding_is_a_snapshot(
    tmp_path,
    monkeypatch,
    imported_names,
):
    (tmp_path / "state.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.append("state")
    module = importlib.import_module("state")
    imported_value = module.value

    module.value = 2

    assert module.value == 2
    assert imported_value == 1


def test_each_module_has_an_independent_global_namespace(tmp_path, monkeypatch, imported_names):
    (tmp_path / "left.py").write_text("label = 'left'\n", encoding="utf-8")
    (tmp_path / "right.py").write_text("label = 'right'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.extend(["left", "right"])

    left = importlib.import_module("left")
    right = importlib.import_module("right")

    assert left.label == "left"
    assert right.label == "right"


def test_all_controls_star_import_not_direct_attribute_access(tmp_path, monkeypatch, imported_names):
    source = "__all__ = ['public']\npublic = 1\n_private = 2\n"
    (tmp_path / "exports.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.append("exports")
    module = importlib.import_module("exports")

    assert module.__all__ == ["public"]
    assert module._private == 2
