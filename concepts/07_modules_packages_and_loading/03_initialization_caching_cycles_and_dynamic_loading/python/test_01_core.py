"""初始化、缓存、循环依赖与动态加载。

共同问题：模块初始化执行几次；缓存键是什么；循环导入看到什么状态；
运行期加载如何报告失败。
"""

# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
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


def test_import_cache_runs_module_body_once(tmp_path, monkeypatch, imported_names):
    marker = tmp_path / "marker.txt"
    source = f"from pathlib import Path\nPath({str(marker)!r}).write_text('run')\n"
    (tmp_path / "cached.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.append("cached")

    first = importlib.import_module("cached")
    second = importlib.import_module("cached")

    assert first is second
    assert marker.read_text(encoding="utf-8") == "run"


def test_reload_reexecutes_code_in_the_existing_module_object(
    tmp_path,
    monkeypatch,
    imported_names,
):
    path = tmp_path / "reloadable.py"
    path.write_text("runs = globals().get('runs', 0) + 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.append("reloadable")
    module = importlib.import_module("reloadable")

    reloaded = importlib.reload(module)

    assert reloaded is module
    assert module.runs == 2


def test_cycle_can_observe_a_partially_initialized_module(tmp_path, monkeypatch, imported_names):
    (tmp_path / "left.py").write_text("label = 'left'\nimport right\nseen = right.label\n", encoding="utf-8")
    (tmp_path / "right.py").write_text("import left\nlabel = left.label + '>right'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    imported_names.extend(["left", "right"])

    left = importlib.import_module("left")

    assert left.seen == "left>right"


def test_dynamic_import_reports_missing_module():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("polyglot_missing_module")
