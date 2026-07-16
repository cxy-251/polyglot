"""160｜importlib：模块规范、finder/loader、缓存和加载工具。

导入不是“找到文件再执行”这么简单：finder 产生 ``ModuleSpec``，
loader 创建并填充模块，导入机械负责 ``sys.modules``、包元数据、
并发和失败回滚。本套从
``import_module/reload`` 的日常工作流进入 ``importlib.abc``、``machinery`` 和
``util``，并用内存 importer、path hook、文件 loader 与 LazyLoader 展示协议。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.importlib python.importlib.import-module
# polyglot-covers: python.importlib.import-vs-builtin-import
# polyglot-covers: python.importlib.relative-import python.importlib.resolve-name
# polyglot-covers: python.importlib.invalidate-caches
# polyglot-covers: python.importlib.reload python.importlib.reload-retained-dict
# polyglot-covers: python.importlib.reload-external-reference
# polyglot-covers: python.importlib.reload-requires-spec
# polyglot-covers: python.stdlib.importlib.abc python.importlib.meta-path-finder
# polyglot-covers: python.importlib.path-entry-finder python.importlib.loader
# polyglot-covers: python.importlib.create-module python.importlib.exec-module
# polyglot-covers: python.importlib.failed-import-cleanup
# polyglot-covers: python.importlib.finder-path-target
# polyglot-covers: python.importlib.inspect-loader python.importlib.source-to-code
# polyglot-covers: python.importlib.finder-abc-change-3.10
# polyglot-covers: python.stdlib.importlib.machinery python.importlib.module-spec
# polyglot-covers: python.importlib.spec-parent-package-location-state
# polyglot-covers: python.importlib.source-file-loader
# polyglot-covers: python.importlib.file-finder python.importlib.path-finder
# polyglot-covers: python.importlib.path-hooks python.importlib.path-importer-cache
# polyglot-covers: python.importlib.builtin-importer python.importlib.frozen-importer
# polyglot-covers: python.importlib.module-suffixes
# polyglot-covers: python.stdlib.importlib.util python.importlib.find-spec
# polyglot-covers: python.importlib.find-spec-parent-side-effect
# polyglot-covers: python.importlib.module-from-spec
# polyglot-covers: python.importlib.spec-from-loader
# polyglot-covers: python.importlib.spec-from-file-location
# polyglot-covers: python.importlib.cache-from-source
# polyglot-covers: python.importlib.source-from-cache
# polyglot-covers: python.importlib.decode-source python.importlib.source-hash
# polyglot-covers: python.importlib.magic-number
# polyglot-covers: python.importlib.lazy-loader python.importlib.lazy-error-context

from contextlib import contextmanager
import importlib
from importlib import abc
from importlib import machinery
from importlib import util
from pathlib import Path
import sys
import types

import pytest


@contextmanager
def isolated_modules(*prefixes):
    """只移除案例新导入的同名前缀，保留测试开始前已有的模块。"""

    existing = set(sys.modules)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name in existing:
                continue
            if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
                sys.modules.pop(name, None)


class MemoryLoader(abc.Loader):
    def __init__(self, values=None, *, fail=False):
        self.values = dict(values or {})
        self.fail = fail
        self.created = []
        self.executed = []

    def create_module(self, spec):
        self.created.append(spec.name)
        # None 委托给导入机械创建普通 ModuleType，并填充规范控制的属性。
        return None

    def exec_module(self, module):
        self.executed.append(module.__name__)
        if self.fail:
            raise RuntimeError("loader execution failed")
        module.__dict__.update(self.values)


class MemoryFinder(abc.MetaPathFinder):
    def __init__(self, loaders):
        self.loaders = loaders
        self.calls = []
        self.invalidations = 0

    def find_spec(self, fullname, path, target=None):
        self.calls.append((fullname, path, target))
        loader = self.loaders.get(fullname)
        if loader is None:
            return None
        is_package = any(name.startswith(fullname + ".") for name in self.loaders)
        return util.spec_from_loader(
            fullname,
            loader,
            origin=f"memory://{fullname}",
            is_package=is_package,
        )

    def invalidate_caches(self):
        self.invalidations += 1


class StringInspectLoader(abc.InspectLoader):
    def __init__(self, sources, packages=()):
        self.sources = sources
        self.packages = set(packages)

    def get_source(self, fullname):
        try:
            return self.sources[fullname]
        except KeyError as error:
            raise ImportError(fullname) from error

    def is_package(self, fullname):
        return fullname in self.packages


class VirtualPathFinder(abc.PathEntryFinder):
    def __init__(self, path_entry, modules):
        self.path_entry = path_entry
        self.modules = modules
        self.queries = []
        self.invalidations = 0

    def find_spec(self, fullname, target=None):
        self.queries.append((fullname, target))
        loader = self.modules.get(fullname)
        if loader is None:
            return None
        return util.spec_from_loader(
            fullname,
            loader,
            origin=f"{self.path_entry}/{fullname}",
        )

    def invalidate_caches(self):
        self.invalidations += 1


def test_import_module_returns_requested_submodule_while_builtin_returns_top_package(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "polyglot_import_api"
    package.mkdir()
    (package / "__init__.py").write_text("package_value = 1\n", encoding="utf-8")
    (package / "child.py").write_text("answer = 42\n", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    with isolated_modules("polyglot_import_api"):
        requested = importlib.import_module("polyglot_import_api.child")
        top_level = builtins_import = __import__("polyglot_import_api.child")

        assert requested.__name__ == "polyglot_import_api.child"
        assert requested.answer == 42
        assert top_level is sys.modules["polyglot_import_api"]
        assert builtins_import.child is requested


def test_relative_import_module_uses_package_as_the_anchor(tmp_path, monkeypatch):
    package = tmp_path / "polyglot_relative_demo"
    subpackage = package / "tools"
    subpackage.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "shared.py").write_text("name = 'shared'\n", encoding="utf-8")
    (subpackage / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    with isolated_modules("polyglot_relative_demo"):
        imported = importlib.import_module("..shared", "polyglot_relative_demo.tools")
        assert imported.__name__ == "polyglot_relative_demo.shared"
        assert imported.name == "shared"

    assert util.resolve_name("..shared", "polyglot_relative_demo.tools") == (
        "polyglot_relative_demo.shared"
    )
    assert util.resolve_name("sys", None) == "sys"
    with pytest.raises(ImportError):
        util.resolve_name(".child", None)
    with pytest.raises(ImportError):
        util.resolve_name("...outside", "one.two")


def test_invalidate_caches_notifies_each_meta_path_finder(monkeypatch):
    finder = MemoryFinder({})
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

    importlib.invalidate_caches()
    assert finder.invalidations == 1


def test_custom_meta_path_finder_and_loader_participate_in_normal_import(monkeypatch):
    name = "polyglot_memory_module"
    loader = MemoryLoader({"answer": 42})
    finder = MemoryFinder({name: loader})
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

    with isolated_modules(name):
        module = importlib.import_module(name)
        assert module.answer == 42
        assert module.__name__ == name
        assert module.__package__ == ""
        assert module.__loader__ is loader
        assert module.__spec__.origin == f"memory://{name}"
        assert module.__spec__.has_location is False
        assert loader.created == [name]
        assert loader.executed == [name]
        assert finder.calls[0] == (name, None, None)


def test_package_submodule_search_passes_parent_path_to_meta_finder(monkeypatch):
    package_name = "polyglot_memory_package"
    child_name = package_name + ".child"
    package_loader = MemoryLoader({"package_loaded": True})
    child_loader = MemoryLoader({"answer": 42})
    finder = MemoryFinder(
        {
            package_name: package_loader,
            child_name: child_loader,
        }
    )
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

    with isolated_modules(package_name):
        child = importlib.import_module(child_name)
        package = sys.modules[package_name]

        assert child.answer == 42
        assert package.package_loaded is True
        assert package.__path__ == []
        assert finder.calls[0] == (package_name, None, None)
        child_call = finder.calls[1]
        assert child_call[0] == child_name
        assert child_call[1] is package.__path__
        assert child_call[2] is None


def test_failed_exec_module_removes_new_partial_module_from_cache(monkeypatch):
    name = "polyglot_failing_import"
    loader = MemoryLoader(fail=True)
    finder = MemoryFinder({name: loader})
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

    with isolated_modules(name):
        with pytest.raises(RuntimeError, match="loader execution failed"):
            importlib.import_module(name)
        assert name not in sys.modules
        assert loader.created == [name]
        assert loader.executed == [name]


def test_reload_refinds_spec_reuses_module_dict_and_does_not_rebind_external_names(
    monkeypatch,
):
    name = "polyglot_reload_demo"

    class ReloadLoader(MemoryLoader):
        def exec_module(self, module):
            self.executed.append(module.__name__)
            version = len(self.executed)
            module.version = version
            module.make_value = lambda: version
            if version == 1:
                module.only_in_first_version = "retained"

    loader = ReloadLoader()
    finder = MemoryFinder({name: loader})
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

    with isolated_modules(name):
        module = importlib.import_module(name)
        old_function = module.make_value
        reloaded = importlib.reload(module)

        assert reloaded is module
        assert module.version == 2
        assert module.make_value() == 2
        assert old_function() == 1
        assert module.only_in_first_version == "retained"
        assert finder.calls[-1] == (name, None, module)
        assert loader.created == [name]
    # reload 保留原模块字典，未在新代码中覆盖的旧名称不会自动删除。


def test_reload_rejects_a_module_without_a_discoverable_spec():
    module = types.ModuleType("polyglot_spec_less_module")
    sys.modules[module.__name__] = module
    try:
        with pytest.raises(ModuleNotFoundError, match="spec not found"):
            importlib.reload(module)
    finally:
        sys.modules.pop(module.__name__, None)


def test_module_spec_models_module_and_package_metadata_without_auto_synchronization():
    loader = MemoryLoader()
    module_spec = machinery.ModuleSpec(
        "demo.child",
        loader,
        origin="memory://demo/child",
        loader_state={"tenant": "teaching"},
        is_package=False,
    )
    package_spec = machinery.ModuleSpec(
        "demo.package",
        loader,
        origin="memory://demo/package",
        is_package=True,
    )

    assert module_spec.name == "demo.child"
    assert module_spec.parent == "demo"
    assert module_spec.submodule_search_locations is None
    assert module_spec.loader_state == {"tenant": "teaching"}
    assert module_spec.has_location is False

    assert package_spec.parent == "demo.package"
    assert package_spec.submodule_search_locations == []
    package_spec.submodule_search_locations.append("memory://portion")
    assert package_spec.submodule_search_locations == ["memory://portion"]


def test_module_from_spec_sets_import_controlled_attributes_before_execution():
    loader = MemoryLoader({"answer": 42})
    spec = util.spec_from_loader(
        "polyglot_manual_module",
        loader,
        origin="memory://manual",
    )
    module = util.module_from_spec(spec)

    assert module.__name__ == "polyglot_manual_module"
    assert module.__spec__ is spec
    assert module.__loader__ is loader
    assert module.__package__ == ""
    assert "answer" not in module.__dict__

    loader.exec_module(module)
    assert module.answer == 42
    assert "polyglot_manual_module" not in sys.modules
    # 手工 recipe 若需支持递归导入，调用者必须在 exec_module 前放入
    # sys.modules；module_from_spec 本身不会修改全局模块缓存。


def test_inspect_loader_compiles_source_and_executes_it_through_concrete_defaults():
    name = "polyglot_string_loaded"
    source = "answer = 6 * 7\n"
    loader = StringInspectLoader({name: source})
    spec = util.spec_from_loader(name, loader, origin="memory://source")
    module = util.module_from_spec(spec)

    assert loader.get_source(name) == source
    code_object = loader.get_code(name)
    assert code_object.co_filename == "<string>"
    loader.exec_module(module)
    assert module.answer == 42
    assert loader.is_package(name) is False
    # 3.10 的 InspectLoader 只要源码就能编译，但不知道文件路径时会把
    # co_filename 设为 "<string>"；ExecutionLoader.get_filename 才能补上
    # 可诊断的真实或虚拟位置。

    compiled = loader.source_to_code("value = 3", "virtual-file.py")
    namespace = {}
    exec(compiled, namespace)
    assert namespace["value"] == 3
    assert compiled.co_filename == "virtual-file.py"


def test_python_310_finder_abcs_are_separate_from_deprecated_finder_base():
    assert not issubclass(abc.MetaPathFinder, abc.Finder)
    assert not issubclass(abc.PathEntryFinder, abc.Finder)
    assert issubclass(MemoryFinder, abc.MetaPathFinder)
    assert issubclass(VirtualPathFinder, abc.PathEntryFinder)
    # 3.10 起两个现代 finder ABC 不再继承已弃用的 Finder；实现 find_spec。


def test_source_file_loader_reads_source_code_and_package_status(tmp_path):
    module_path = tmp_path / "file_loaded.py"
    module_path.write_text("answer = 42\n", encoding="utf-8")
    loader = machinery.SourceFileLoader("file_loaded", str(module_path))

    assert loader.get_filename("file_loaded") == str(module_path)
    assert loader.get_source("file_loaded") == "answer = 42\n"
    assert loader.is_package("file_loaded") is False
    code_object = loader.get_code("file_loaded")
    assert code_object.co_filename == str(module_path)

    spec = util.spec_from_file_location("file_loaded", module_path, loader=loader)
    module = util.module_from_spec(spec)
    loader.exec_module(module)
    assert module.answer == 42
    assert module.__file__ == str(module_path)


def test_spec_from_file_location_infers_loader_cache_and_location(tmp_path):
    module_path = tmp_path / "direct_module.py"
    module_path.write_text("value = 'loaded'\n", encoding="utf-8")
    spec = util.spec_from_file_location("direct_module", module_path)

    assert isinstance(spec.loader, machinery.SourceFileLoader)
    assert spec.origin == str(module_path)
    assert spec.has_location is True
    assert spec.cached == util.cache_from_source(module_path)
    assert spec.submodule_search_locations is None

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.value == "loaded"


def test_path_finder_and_file_finder_locate_source_without_importing_it(tmp_path):
    module_path = tmp_path / "discoverable.py"
    module_path.write_text("loaded = True\n", encoding="utf-8")

    path_spec = machinery.PathFinder.find_spec("discoverable", [str(tmp_path)])
    assert path_spec.name == "discoverable"
    assert path_spec.origin == str(module_path)
    assert "discoverable" not in sys.modules

    file_finder = machinery.FileFinder(
        str(tmp_path),
        (machinery.SourceFileLoader, machinery.SOURCE_SUFFIXES),
    )
    direct_spec = file_finder.find_spec("discoverable")
    assert direct_spec.origin == str(module_path)
    assert file_finder.find_spec("missing_module") is None


def test_custom_path_hook_is_cached_per_path_entry_and_can_be_invalidated(monkeypatch):
    path_entry = "polyglot-memory://modules"
    module_name = "polyglot_path_hook_module"
    loader = MemoryLoader({"answer": 42})
    created_finders = []

    def path_hook(path):
        if path != path_entry:
            raise ImportError
        finder = VirtualPathFinder(path, {module_name: loader})
        created_finders.append(finder)
        return finder

    monkeypatch.setattr(sys, "path_hooks", [path_hook, *sys.path_hooks])
    monkeypatch.setattr(sys, "path_importer_cache", sys.path_importer_cache.copy())
    monkeypatch.setattr(sys, "path", [path_entry, *sys.path])

    with isolated_modules(module_name):
        module = importlib.import_module(module_name)
        assert module.answer == 42
        assert len(created_finders) == 1
        assert sys.path_importer_cache[path_entry] is created_finders[0]

        assert importlib.import_module(module_name) is module
        assert len(created_finders) == 1

        importlib.invalidate_caches()
        assert created_finders[0].invalidations == 1


def test_builtin_and_frozen_importers_expose_specs_for_supported_modules():
    builtin_spec = machinery.BuiltinImporter.find_spec("sys")
    assert builtin_spec.name == "sys"
    assert builtin_spec.origin == "built-in"
    assert builtin_spec.loader is machinery.BuiltinImporter
    assert machinery.BuiltinImporter.get_code("sys") is None
    assert machinery.BuiltinImporter.get_source("sys") is None

    assert machinery.FrozenImporter.find_spec("a-module-that-is-not-frozen") is None


def test_machinery_suffix_sets_describe_recognized_module_file_kinds():
    suffixes = machinery.all_suffixes()
    assert ".py" in machinery.SOURCE_SUFFIXES
    assert ".pyc" in machinery.BYTECODE_SUFFIXES
    assert set(machinery.SOURCE_SUFFIXES) <= set(suffixes)
    assert set(machinery.BYTECODE_SUFFIXES) <= set(suffixes)
    assert set(machinery.EXTENSION_SUFFIXES) <= set(suffixes)
    assert machinery.DEBUG_BYTECODE_SUFFIXES is machinery.BYTECODE_SUFFIXES
    assert machinery.OPTIMIZED_BYTECODE_SUFFIXES is machinery.BYTECODE_SUFFIXES


def test_find_spec_reports_metadata_without_importing_top_level_module(tmp_path, monkeypatch):
    module_path = tmp_path / "polyglot_spec_probe.py"
    module_path.write_text("executed = True\n", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    with isolated_modules("polyglot_spec_probe"):
        spec = util.find_spec("polyglot_spec_probe")
        assert spec.name == "polyglot_spec_probe"
        assert spec.origin == str(module_path)
        assert "polyglot_spec_probe" not in sys.modules

        missing = util.find_spec("polyglot_module_that_does_not_exist")
        assert missing is None


def test_find_spec_imports_parent_when_resolving_a_dotted_name(tmp_path, monkeypatch):
    package = tmp_path / "polyglot_spec_parent"
    package.mkdir()
    (package / "__init__.py").write_text("parent_executed = True\n", encoding="utf-8")
    (package / "child.py").write_text("child_executed = True\n", encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)

    with isolated_modules("polyglot_spec_parent"):
        spec = util.find_spec("polyglot_spec_parent.child")
        assert spec.name == "polyglot_spec_parent.child"
        assert "polyglot_spec_parent" in sys.modules
        assert sys.modules["polyglot_spec_parent"].parent_executed is True
        assert "polyglot_spec_parent.child" not in sys.modules


def test_cache_path_helpers_encode_tag_and_optimization_without_touching_disk(tmp_path):
    source = tmp_path / "package" / "module.py"
    ordinary = Path(util.cache_from_source(source))
    optimized = Path(util.cache_from_source(source, optimization=2))

    assert ordinary.parent.name == "__pycache__"
    assert sys.implementation.cache_tag in ordinary.name
    assert ordinary.name.endswith(".pyc")
    assert ".opt-2.pyc" in optimized.name
    assert Path(util.source_from_cache(optimized)) == source
    assert not ordinary.exists()

    with pytest.raises(ValueError, match="alphanumeric"):
        util.cache_from_source(source, optimization="not-valid!")
    with pytest.raises(ValueError):
        util.source_from_cache(tmp_path / "module.pyc")


def test_decode_source_honors_cookie_bom_and_universal_newlines():
    latin_1 = b"# coding: latin-1\r\nname = 'caf\xe9'\r\n"
    decoded = util.decode_source(latin_1)
    assert decoded == "# coding: latin-1\nname = 'caf\xe9'\n"

    utf_8_bom = b"\xef\xbb\xbfvalue = '\xe4\xbd\xa0\xe5\xa5\xbd'\r\n"
    assert util.decode_source(utf_8_bom) == "value = '\u4f60\u597d'\n"


def test_magic_number_and_source_hash_are_versioned_bytecode_building_blocks():
    assert isinstance(util.MAGIC_NUMBER, bytes)
    assert len(util.MAGIC_NUMBER) == 4
    first = util.source_hash(b"answer = 42\n")
    same = util.source_hash(b"answer = 42\n")
    different = util.source_hash(b"answer = 43\n")

    assert first == same
    assert first != different
    assert isinstance(first, bytes)
    assert len(first) == 8


def test_lazy_loader_defers_module_body_until_first_attribute_access(tmp_path):
    name = "polyglot_lazy_module"
    marker = tmp_path / "lazy-executed.txt"
    module_path = tmp_path / f"{name}.py"
    module_path.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "answer = 42\n",
        encoding="utf-8",
    )
    spec = util.spec_from_file_location(name, module_path)
    lazy_loader = util.LazyLoader(spec.loader)
    spec.loader = lazy_loader
    module = util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        lazy_loader.exec_module(module)
        assert not marker.exists()

        assert module.answer == 42
        assert marker.read_text(encoding="utf-8") == "executed"
    finally:
        sys.modules.pop(name, None)
    # 延迟加载会把导入错误推迟到属性访问，错误位置可能远离真正
    # 导入点；只有启动时间收益明确时才值得接受这项诊断成本。
