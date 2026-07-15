"""162｜pkgutil、modulefinder 与 runpy：发现、静态分析和脚本式执行。

三个模块都“寻找模块”但目的不同：``pkgutil`` 枚举 package 与读取 loader
数据，
``modulefinder`` 静态扫描字节码中的 import，``runpy`` 则真的在当前进程执行模块
或路径。本套明确区分发现与执行副作用，并把会改 modulefinder
全局兼容映射的
旧 API 放入子进程隔离。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.pkgutil python.pkgutil.module-info
# polyglot-covers: python.pkgutil.extend-path python.pkgutil.split-package
# polyglot-covers: python.pkgutil.pkg-file-trusted-paths
# polyglot-covers: python.pkgutil.get-importer python.pkgutil.importer-cache
# polyglot-covers: python.pkgutil.find-loader python.pkgutil.get-loader
# polyglot-covers: python.pkgutil.iter-importers
# polyglot-covers: python.pkgutil.iter-modules python.pkgutil.walk-packages
# polyglot-covers: python.pkgutil.walk-imports-packages python.pkgutil.onerror
# polyglot-covers: python.pkgutil.get-data python.pkgutil.loader-get-data
# polyglot-covers: python.pkgutil.namespace-get-data-none
# polyglot-covers: python.pkgutil.resolve-name python.pkgutil.resolve-colon
# polyglot-covers: python.pkgutil.imp-importer-loader-deprecated
# polyglot-covers: python.stdlib.modulefinder python.modulefinder.module-finder
# polyglot-covers: python.modulefinder.run-script python.modulefinder.modules
# polyglot-covers: python.modulefinder.bad-modules python.modulefinder.global-names
# polyglot-covers: python.modulefinder.excludes python.modulefinder.replace-paths
# polyglot-covers: python.modulefinder.report
# polyglot-covers: python.modulefinder.add-package-path
# polyglot-covers: python.modulefinder.replace-package
# polyglot-covers: python.stdlib.runpy python.runpy.run-module
# polyglot-covers: python.runpy.fresh-namespace python.runpy.init-globals
# polyglot-covers: python.runpy.special-globals python.runpy.run-name-spec-name
# polyglot-covers: python.runpy.package-main python.runpy.relative-import
# polyglot-covers: python.runpy.alter-sys python.runpy.thread-safety
# polyglot-covers: python.runpy.side-effects-not-sandbox
# polyglot-covers: python.runpy.run-path python.runpy.script-metadata
# polyglot-covers: python.runpy.run-path-directory-main
# polyglot-covers: python.runpy.sys-restoration

from contextlib import contextmanager
from contextlib import redirect_stdout
import importlib
from importlib import machinery
from io import StringIO
import json
import modulefinder
import os
from pathlib import Path
import pkgutil
import runpy
import subprocess
import sys

import pytest


@contextmanager
def remove_new_modules(*prefixes):
    existing = set(sys.modules)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name in existing:
                continue
            if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
                sys.modules.pop(name, None)


def make_discovery_tree(root):
    package = root / "polyglot_discovery"
    subpackage = package / "subpkg"
    subpackage.mkdir(parents=True)
    (package / "__init__.py").write_text("PACKAGE_IMPORTED = True\n", encoding="utf-8")
    (package / "alpha.py").write_text("VALUE = 'alpha'\n", encoding="utf-8")
    (package / "data.bin").write_bytes(b"package-data")
    (subpackage / "__init__.py").write_text("SUBPACKAGE_IMPORTED = True\n", encoding="utf-8")
    (subpackage / "child.py").write_text("VALUE = 'child'\n", encoding="utf-8")
    (root / "top_level_module.py").write_text("VALUE = 'top'\n", encoding="utf-8")
    return package


def test_module_info_is_a_named_tuple_for_finder_name_and_package_flag():
    finder = object()
    information = pkgutil.ModuleInfo(finder, "demo.module", True)
    assert information.module_finder is finder
    assert information.name == "demo.module"
    assert information.ispkg is True
    assert tuple(information) == (finder, "demo.module", True)


def test_extend_path_combines_split_package_directories_without_mutating_input(
    tmp_path,
    monkeypatch,
):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_package = first_root / "polyglot_split"
    second_package = second_root / "polyglot_split"
    first_package.mkdir(parents=True)
    second_package.mkdir(parents=True)
    original = [str(first_package)]
    monkeypatch.setattr(sys, "path", [str(first_root), str(second_root)])

    extended = pkgutil.extend_path(original, "polyglot_split")
    assert original == [str(first_package)]
    assert extended == [str(first_package), str(second_package)]
    assert extended is not original


def test_extend_path_trusts_pkg_file_entries_even_when_they_do_not_exist(
    tmp_path,
    monkeypatch,
):
    package_root = tmp_path / "root"
    package = package_root / "polyglot_split"
    package.mkdir(parents=True)
    declared = tmp_path / "not-created" / "portion"
    (package_root / "polyglot_split.pkg").write_text(
        "# comment\n"
        f"{declared}\n"
        f"{declared}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "path", [str(package_root)])

    extended = pkgutil.extend_path([str(package)], "polyglot_split")
    assert extended == [str(package), str(declared), str(declared)]
    assert not declared.exists()
    # .pkg 与 .pth 不同：没有 import 行语义，路径按受信配置原样加入；
    # 文件里重复的行也会重复出现，不要把它当成去重配置格式。


def test_extend_path_returns_non_list_input_unchanged():
    frozen_style_path = ("one", "two")
    assert pkgutil.extend_path(frozen_style_path, "demo") is frozen_style_path


def test_get_importer_uses_path_hooks_and_caches_the_result(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "path_importer_cache", sys.path_importer_cache.copy())
    path = str(tmp_path)
    sys.path_importer_cache.pop(path, None)

    first = pkgutil.get_importer(path)
    second = pkgutil.get_importer(path)
    assert isinstance(first, machinery.FileFinder)
    assert second is first
    assert sys.path_importer_cache[path] is first


def test_find_loader_and_get_loader_wrap_spec_lookup(tmp_path, monkeypatch):
    module_path = tmp_path / "polyglot_loader_probe.py"
    module_path.write_text("VALUE = 42\n", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    loader = pkgutil.find_loader("polyglot_loader_probe")
    assert isinstance(loader, machinery.SourceFileLoader)
    assert pkgutil.get_loader("polyglot_loader_probe").path == str(module_path)
    assert pkgutil.get_loader("polyglot_missing_loader") is None


def test_get_loader_accepts_a_module_object_as_well_as_a_name():
    assert pkgutil.get_loader(pkgutil) is pkgutil.__loader__
    assert pkgutil.get_loader("pkgutil") is pkgutil.__loader__


def test_iter_importers_includes_meta_path_finders_for_top_level_names():
    importers = list(pkgutil.iter_importers("polyglot_top_level_probe"))
    meta_path_prefix = importers[: len(sys.meta_path)]
    assert meta_path_prefix == sys.meta_path
    assert machinery.PathFinder in meta_path_prefix
    # 顶层名称先枚举 meta_path，再查询每个 sys.path 项的 importer；
    # 后半段可能包含 None，因为不是所有路径都被 path hook 接受。


def test_iter_modules_lists_one_level_without_importing_packages(tmp_path):
    make_discovery_tree(tmp_path)
    assert "polyglot_discovery" not in sys.modules

    found = {
        information.name: information
        for information in pkgutil.iter_modules([str(tmp_path)], prefix="prefix.")
    }
    assert found["prefix.polyglot_discovery"].ispkg is True
    assert found["prefix.top_level_module"].ispkg is False
    assert "polyglot_discovery" not in sys.modules


def test_walk_packages_recurses_by_importing_packages_but_not_leaf_modules(
    tmp_path,
    monkeypatch,
):
    package = make_discovery_tree(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    with remove_new_modules("polyglot_discovery"):
        found = {
            information.name: information
            for information in pkgutil.walk_packages(
                [str(package)],
                prefix="polyglot_discovery.",
            )
        }
        assert set(found) == {
            "polyglot_discovery.alpha",
            "polyglot_discovery.subpkg",
            "polyglot_discovery.subpkg.child",
        }
        assert "polyglot_discovery.subpkg" in sys.modules
        assert "polyglot_discovery.alpha" not in sys.modules
        assert "polyglot_discovery.subpkg.child" not in sys.modules


def test_walk_packages_onerror_receives_package_whose_import_failed(
    tmp_path,
    monkeypatch,
):
    broken = tmp_path / "broken_discovery"
    broken.mkdir()
    (broken / "__init__.py").write_text(
        "raise RuntimeError('broken package import')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path)
    errors = []

    with remove_new_modules("broken_discovery"):
        found = list(
            pkgutil.walk_packages(
                [str(tmp_path)],
                onerror=errors.append,
            )
        )
    assert any(item.name == "broken_discovery" and item.ispkg for item in found)
    assert errors == ["broken_discovery"]


def test_get_data_reads_nested_package_resource_through_loader(tmp_path, monkeypatch):
    package = make_discovery_tree(tmp_path)
    (package / "nested").mkdir()
    (package / "nested" / "payload.txt").write_text("nested data", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    with remove_new_modules("polyglot_discovery"):
        assert pkgutil.get_data("polyglot_discovery", "data.bin") == b"package-data"
        assert pkgutil.get_data("polyglot_discovery", "nested/payload.txt") == b"nested data"


def test_get_data_returns_none_for_namespace_package_without_get_data_loader(
    tmp_path,
    monkeypatch,
):
    namespace = tmp_path / "polyglot_namespace_data"
    namespace.mkdir()
    (namespace / "resource.txt").write_text("unavailable", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    with remove_new_modules("polyglot_namespace_data"):
        imported = importlib.import_module("polyglot_namespace_data")
        spec = imported.__spec__
        assert spec.submodule_search_locations is not None
        assert spec.loader is None or not hasattr(spec.loader, "get_data")
        assert pkgutil.get_data("polyglot_namespace_data", "resource.txt") is None


def test_resolve_name_prefers_explicit_module_object_boundary():
    assert pkgutil.resolve_name("json:loads") is json.loads
    assert pkgutil.resolve_name("pathlib:Path.read_text") is Path.read_text
    assert pkgutil.resolve_name("json:") is json
    assert pkgutil.resolve_name("json.decoder.JSONDecoder") is json.decoder.JSONDecoder

    with pytest.raises(ValueError):
        pkgutil.resolve_name("not valid:object")
    with pytest.raises(AttributeError):
        pkgutil.resolve_name("json:missing_attribute")


def test_imp_importer_and_loader_are_retained_only_for_legacy_compatibility():
    assert issubclass(pkgutil.ImpImporter, object)
    assert issubclass(pkgutil.ImpLoader, object)
    assert pkgutil.ImpImporter is not machinery.FileFinder
    assert pkgutil.ImpLoader is not machinery.SourceFileLoader
    # 两者只包装旧 imp 算法；新 finder/loader 应直接使用 importlib 协议。


def test_modulefinder_analyzes_imports_globals_and_missing_modules(tmp_path):
    package = tmp_path / "analysis_package"
    package.mkdir()
    (package / "__init__.py").write_text("PACKAGE_VALUE = 1\n", encoding="utf-8")
    (package / "helper.py").write_text("HELPER_VALUE = 2\n", encoding="utf-8")
    script = tmp_path / "application.py"
    script.write_text(
        "import json\n"
        "from analysis_package import helper\n"
        "try:\n"
        "    import definitely_missing_dependency\n"
        "except ImportError:\n"
        "    definitely_missing_dependency = None\n"
        "RESULT = helper.HELPER_VALUE\n",
        encoding="utf-8",
    )
    finder = modulefinder.ModuleFinder(path=[str(tmp_path), *sys.path])
    finder.run_script(str(script))

    assert {"__main__", "json", "analysis_package", "analysis_package.helper"} <= set(
        finder.modules
    )
    assert "definitely_missing_dependency" in finder.badmodules
    main_module = finder.modules["__main__"]
    assert {"json", "helper", "definitely_missing_dependency", "RESULT"} <= set(
        main_module.globalnames
    )
    assert main_module.__file__ == str(script)


def test_modulefinder_excludes_named_modules_from_analysis(tmp_path):
    script = tmp_path / "application.py"
    script.write_text("import json\nimport decimal\n", encoding="utf-8")
    finder = modulefinder.ModuleFinder(excludes=["decimal"])
    finder.run_script(str(script))

    assert "json" in finder.modules
    assert "decimal" not in finder.modules
    assert "decimal" not in finder.badmodules


def test_modulefinder_replace_paths_rewrites_recorded_code_filenames(tmp_path):
    script = tmp_path / "application.py"
    script.write_text("value = 42\n", encoding="utf-8")
    finder = modulefinder.ModuleFinder(
        path=[str(tmp_path), *sys.path],
        replace_paths=[(str(tmp_path), "<project>")],
    )
    finder.run_script(str(script))

    code_object = finder.modules["__main__"].__code__
    assert code_object.co_filename == os.path.join("<project>", "application.py")


def test_modulefinder_report_prints_loaded_and_missing_sections(tmp_path):
    script = tmp_path / "application.py"
    script.write_text("import json\nimport missing_for_report\n", encoding="utf-8")
    finder = modulefinder.ModuleFinder()
    finder.run_script(str(script))

    output = StringIO()
    with redirect_stdout(output):
        finder.report()
    report = output.getvalue()
    assert "Name" in report
    assert "__main__" in report
    assert "json" in report
    assert "Missing modules:" in report
    assert "missing_for_report" in report


def test_modulefinder_global_compatibility_maps_are_isolated_in_child(tmp_path):
    main_root = tmp_path / "main"
    extra_root = tmp_path / "extra"
    package = main_root / "legacy_package"
    extra_package = extra_root / "legacy_package"
    package.mkdir(parents=True)
    extra_package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (extra_package / "extra.py").write_text("VALUE = 42\n", encoding="utf-8")
    script = tmp_path / "application.py"
    script.write_text(
        "import legacy_package.extra\n"
        "import legacy_alias\n",
        encoding="utf-8",
    )
    (main_root / "legacy_alias.py").write_text("VALUE = 'alias'\n", encoding="utf-8")
    program = """
import json
import modulefinder
import sys

main_root, extra_package, script = sys.argv[1:]
modulefinder.AddPackagePath("legacy_package", extra_package)
modulefinder.ReplacePackage("legacy_alias", "canonical_alias")
finder = modulefinder.ModuleFinder(path=[main_root] + sys.path)
finder.run_script(script)
print(json.dumps({
    "has_extra": "legacy_package.extra" in finder.modules,
    "has_old": "legacy_alias" in finder.modules,
    "has_new": "canonical_alias" in finder.modules,
}))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            program,
            str(main_root),
            str(extra_package),
            str(script),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result == {"has_extra": True, "has_old": False, "has_new": True}


def test_run_module_executes_in_fresh_namespace_and_preserves_input_mapping(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "polyglot_run_module.py"
    module.write_text(
        "result = seed + 2\n"
        "observed_name = __name__\n"
        "observed_spec_name = __spec__.name\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path)
    initial = {"seed": 40, "__name__": "wrong", "untouched": []}

    with remove_new_modules("polyglot_run_module"):
        result = runpy.run_module(
            "polyglot_run_module",
            init_globals=initial,
            run_name="teaching.__main__",
        )

    assert initial == {"seed": 40, "__name__": "wrong", "untouched": []}
    assert result["result"] == 42
    assert result["observed_name"] == "teaching.__main__"
    assert result["observed_spec_name"] == "polyglot_run_module"
    assert result["untouched"] is initial["untouched"]
    assert "polyglot_run_module" not in sys.modules


def test_run_module_on_package_executes_main_with_package_for_relative_imports(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "polyglot_runnable_package"
    package.mkdir()
    (package / "__init__.py").write_text("PACKAGE_IMPORTED = True\n", encoding="utf-8")
    (package / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
    (package / "__main__.py").write_text(
        "from .helper import VALUE\n"
        "observed_name = __name__\n"
        "observed_spec = __spec__.name\n"
        "observed_package = __package__\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path)

    with remove_new_modules("polyglot_runnable_package"):
        result = runpy.run_module("polyglot_runnable_package", run_name="cli")
        assert result["VALUE"] == 42
        assert result["observed_name"] == "cli"
        assert result["observed_spec"] == "polyglot_runnable_package.__main__"
        assert result["observed_package"] == "polyglot_runnable_package"


def test_run_module_alter_sys_temporarily_installs_module_and_argv0(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "polyglot_alter_sys.py"
    module.write_text(
        "import sys\n"
        "observed_argv0 = sys.argv[0]\n"
        "observed_cached_self = sys.modules[__name__].__dict__ is globals()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path)
    original_argv0 = sys.argv[0]
    sentinel = object()
    sys.modules["temporary_run_name"] = sentinel
    try:
        result = runpy.run_module(
            "polyglot_alter_sys",
            run_name="temporary_run_name",
            alter_sys=True,
        )
        assert Path(result["observed_argv0"]) == module
        assert result["observed_cached_self"] is True
        assert sys.argv[0] == original_argv0
        assert sys.modules["temporary_run_name"] is sentinel
    finally:
        sys.modules.pop("temporary_run_name", None)
        sys.modules.pop("polyglot_alter_sys", None)
    # alter_sys 修改全局 argv/modules，官方明确指出它不是线程安全接口。


def test_run_module_side_effect_imports_remain_because_runpy_is_not_a_sandbox(
    tmp_path,
    monkeypatch,
):
    (tmp_path / "polyglot_side_effect_helper.py").write_text(
        "VALUE = 42\n",
        encoding="utf-8",
    )
    (tmp_path / "polyglot_side_effect_runner.py").write_text(
        "import polyglot_side_effect_helper\n"
        "result = polyglot_side_effect_helper.VALUE\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path)

    with remove_new_modules("polyglot_side_effect_runner", "polyglot_side_effect_helper"):
        result = runpy.run_module("polyglot_side_effect_runner")
        assert result["result"] == 42
        assert "polyglot_side_effect_helper" in sys.modules
        assert "polyglot_side_effect_runner" not in sys.modules


def test_run_path_script_sets_script_metadata_and_overrides_special_initials(tmp_path):
    script = tmp_path / "standalone.py"
    script.write_text(
        "result = seed + 2\n"
        "observed = (__name__, __spec__, __package__, __cached__, __loader__)\n",
        encoding="utf-8",
    )
    initial = {"seed": 40, "__name__": "wrong"}
    result = runpy.run_path(str(script), init_globals=initial, run_name="script_main")

    assert initial == {"seed": 40, "__name__": "wrong"}
    assert result["result"] == 42
    assert result["observed"] == ("script_main", None, "", None, None)
    assert Path(result["__file__"]) == script
    # run_name 没有点号时，run_path 把其父包名设为空字符串，而非 None。


def test_run_path_directory_executes_main_and_restores_sys_state(tmp_path):
    application = tmp_path / "application"
    application.mkdir()
    (application / "__main__.py").write_text(
        "import sys\n"
        "value = 42\n"
        "observed_name = __name__\n"
        "observed_spec = __spec__.name\n"
        "observed_argv0 = sys.argv[0]\n"
        "observed_path0 = sys.path[0]\n",
        encoding="utf-8",
    )
    original_path = sys.path.copy()
    original_argv0 = sys.argv[0]

    result = runpy.run_path(str(application), run_name="directory_cli")
    assert result["value"] == 42
    assert result["observed_name"] == "directory_cli"
    assert result["observed_spec"] == "__main__"
    assert Path(result["observed_argv0"]) == application
    assert Path(result["observed_path0"]) == application
    assert sys.path == original_path
    assert sys.argv[0] == original_argv0
