"""018｜import 名字绑定、module/package 上下文与缓存语义示例。

import 同时完成“查找/加载 module”和“在当前作用域绑定名称”，两部分不能混为
一谈。首次导入通常执行模块代码并把 module object 放进 ``sys.modules``；后续
导入直接复用缓存。package 为相对导入提供 ``__package__`` 上下文，reload 则
重新执行现有 module，却不会先清空它的字典。

动态案例只在 pytest ``tmp_path`` 创建独特模块，并显式清理 ``sys.modules``。
内容基于 Python 3.10 Import statement / Import system、Modules data model、
importlib、__import__ 与 runpy；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.statement.import python.statement.from-import
# polyglot-covers: python.statement.import-as python.statement.star-import
# polyglot-covers: python.builtin.__import__ python.module.metadata
# polyglot-covers: python.module.sys-modules-cache
# polyglot-covers: python.package.absolute-import python.package.relative-import
# polyglot-covers: python.package.__all__ python.stdlib.importlib.import_module
# polyglot-covers: python.stdlib.importlib.reload python.stdlib.runpy.run_path

import importlib
import runpy
import sys
import types

import pytest


def _write_source(path, source):
    """写入隔离测试模块并让 import finder 放弃旧目录缓存。"""

    path.write_text(source, encoding="utf-8")
    importlib.invalidate_caches()


def _remove_modules(prefix):
    """删除一个独特测试 package/module 及其全部子模块缓存。"""

    for name in list(sys.modules):
        if name == prefix or name.startswith(f"{prefix}."):
            sys.modules.pop(name, None)


def test_import_forms_bind_module_alias_and_selected_attribute_differently():
    """三种 import 外观分别绑定模块名、alias 或模块中的一个属性。"""

    import math
    import math as arithmetic
    from math import sqrt as square_root

    assert isinstance(math, types.ModuleType)
    assert arithmetic is math
    assert square_root is math.sqrt
    assert square_root(9) == 3

    # `from module import name` 把当时取得的对象直接绑定到当前作用域；它不是
    # 每次使用都重新查询 module.name。


def test_import_dotted_name_binds_top_package_while_importlib_returns_submodule():
    """``import package.submodule`` 的普通绑定与 API 返回对象不同。"""

    import xml.sax

    imported = importlib.import_module("xml.sax")

    assert isinstance(xml, types.ModuleType)
    assert imported is xml.sax
    assert "sax" not in locals()

    # import xml.sax 在当前作用域绑定 xml，子模块通过 xml.sax 到达；显式 alias
    # `import xml.sax as sax` 才会绑定本地 sax。


def test_import_builtin_returns_top_package_unless_fromlist_is_nonempty():
    """直接使用 ``__import__`` 时，fromlist 会改变返回层级。"""

    top = __import__("xml.sax")
    submodule = __import__("xml.sax", fromlist=["sax"])

    assert top.__name__ == "xml"
    assert submodule.__name__ == "xml.sax"
    assert top.sax is submodule

    # 日常代码应优先使用 import 语句或 importlib.import_module；__import__ 是
    # import 语句使用的低层 hook，默认返回顶层包的行为很容易误解。


def test_imported_module_exposes_standard_metadata(tmp_path, monkeypatch):
    """loader 为普通文件模块填充名称、package、spec 和来源路径。"""

    module_name = "polyglot_metadata_example"
    module_path = tmp_path / f"{module_name}.py"
    _write_source(module_path, "VALUE = 42\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        module = importlib.import_module(module_name)

        assert module.__name__ == module_name
        assert module.__package__ == ""
        assert module.__spec__.name == module_name
        assert module.__spec__.parent == ""
        assert module.__file__ == str(module_path)
        assert module.VALUE == 42
    finally:
        _remove_modules(module_name)


def test_import_executes_once_then_reuses_sys_modules_cache(tmp_path, monkeypatch):
    """重复 import 返回同一 module；删除缓存后才重新创建并执行。"""

    module_name = "polyglot_cache_example"
    module_path = tmp_path / f"{module_name}.py"
    counter_path = tmp_path / "execution-count.txt"
    source = f"""
from pathlib import Path

counter_path = Path({str(counter_path)!r})
try:
    previous = int(counter_path.read_text(encoding="utf-8"))
except FileNotFoundError:
    previous = 0
execution_number = previous + 1
counter_path.write_text(str(execution_number), encoding="utf-8")
"""
    _write_source(module_path, source)
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        first = importlib.import_module(module_name)
        second = importlib.import_module(module_name)

        assert first is second
        assert first.execution_number == 1
        assert counter_path.read_text(encoding="utf-8") == "1"
        assert sys.modules[module_name] is first

        del sys.modules[module_name]
        third = importlib.import_module(module_name)

        assert third is not first
        assert third.execution_number == 2
        assert counter_path.read_text(encoding="utf-8") == "2"
    finally:
        _remove_modules(module_name)

    # 只修改 .py 文件后再写 import 并不会重跑顶层代码，因为缓存键仍存在。


def test_package_relative_and_absolute_imports_share_the_same_helper_module(
    tmp_path, monkeypatch
):
    """package context 让 ``.helper`` 与完整绝对名称解析到同一 module。"""

    package_name = "polyglot_relative_package"
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    _write_source(package_dir / "__init__.py", 'PACKAGE_MARKER = "loaded"\n')
    _write_source(package_dir / "helper.py", 'VALUE = "shared"\n')
    _write_source(
        package_dir / "consumer.py",
        f"""
from . import helper as relative_helper
from {package_name} import helper as absolute_helper

SAME_OBJECT = relative_helper is absolute_helper
VALUE = relative_helper.VALUE
""",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        consumer = importlib.import_module(f"{package_name}.consumer")
        package = sys.modules[package_name]
        helper = sys.modules[f"{package_name}.helper"]

        assert package.PACKAGE_MARKER == "loaded"
        assert consumer.SAME_OBJECT is True
        assert consumer.VALUE == "shared"
        assert consumer.__package__ == package_name
        assert consumer.__spec__.parent == package_name
        assert package.helper is helper
    finally:
        _remove_modules(package_name)


def test_relative_import_without_package_context_fails(tmp_path, monkeypatch):
    """顶层模块的 ``__package__`` 为空，无法解释前导点。"""

    module_name = "polyglot_top_level_relative_failure"
    _write_source(tmp_path / f"{module_name}.py", "from .helper import VALUE\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        with pytest.raises(ImportError, match="no known parent package"):
            importlib.import_module(module_name)
    finally:
        _remove_modules(module_name)


def test_star_import_obeys_all_even_for_underscored_names():
    """定义 ``__all__`` 后，star import 只导入其中列出的名称。"""

    module_name = "polyglot_star_all_example"
    module = types.ModuleType(module_name)
    module.public = "public"
    module._explicit_private = "included by __all__"
    module.not_exported = "hidden by __all__"
    module.__all__ = ["public", "_explicit_private"]
    sys.modules[module_name] = module

    namespace = {}
    try:
        exec(f"from {module_name} import *", namespace)

        assert namespace["public"] == "public"
        assert namespace["_explicit_private"] == "included by __all__"
        assert "not_exported" not in namespace
    finally:
        _remove_modules(module_name)


def test_star_import_without_all_excludes_leading_underscore_names():
    """未定义 ``__all__`` 时，默认公开 module 中不以下划线开头的名称。"""

    module_name = "polyglot_star_default_example"
    module = types.ModuleType(module_name)
    module.public = "visible"
    module._private = "not imported"
    sys.modules[module_name] = module

    namespace = {}
    try:
        exec(f"from {module_name} import *", namespace)

        assert namespace["public"] == "visible"
        assert "_private" not in namespace
    finally:
        _remove_modules(module_name)

    # star import 会把来源不明的大量名称写进当前命名空间，容易覆盖已有绑定；
    # 正常模块应优先显式列出需要的名称。


def test_reload_reexecutes_but_keeps_module_object_and_old_dictionary_names(
    tmp_path, monkeypatch
):
    """``reload`` 复用 module/dict，未在新执行中覆盖或删除的旧名称仍存在。"""

    module_name = "polyglot_reload_example"
    module_path = tmp_path / f"{module_name}.py"
    state_path = tmp_path / "reload-state.txt"
    state_path.write_text("1", encoding="utf-8")
    source = f"""
from pathlib import Path

revision = int(Path({str(state_path)!r}).read_text(encoding="utf-8"))
current = f"version-{{revision}}"
if revision == 1:
    legacy_name = "defined only during first execution"
"""
    _write_source(module_path, source)
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        module = importlib.import_module(module_name)
        imported_binding = module.current

        assert imported_binding == "version-1"
        assert module.legacy_name.startswith("defined only")

        state_path.write_text("2", encoding="utf-8")
        reloaded = importlib.reload(module)

        assert reloaded is module
        assert module.current == "version-2"
        assert module.legacy_name.startswith("defined only")
        assert imported_binding == "version-1"
    finally:
        _remove_modules(module_name)

    # `from module import current` 的效果也只是复制当时对象；reload 更新
    # module.current，不会追踪并重绑其他作用域里的 imported_binding。


def test_failed_first_import_removes_new_module_from_sys_modules(
    tmp_path, monkeypatch
):
    """模块顶层执行失败时，新插入的缓存项会被移除。"""

    module_name = "polyglot_failed_import_example"
    _write_source(
        tmp_path / f"{module_name}.py",
        'PARTIAL = "set before failure"\nraise RuntimeError("import failed")\n',
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        with pytest.raises(RuntimeError, match="import failed"):
            importlib.import_module(module_name)

        assert module_name not in sys.modules
    finally:
        _remove_modules(module_name)


def test_circular_from_import_reads_a_partially_initialized_module(
    tmp_path, monkeypatch
):
    """循环中 ``from module import name`` 可能在对方定义该名称之前就读取。"""

    left_name = "polyglot_cycle_left"
    right_name = "polyglot_cycle_right"
    _write_source(
        tmp_path / f"{left_name}.py",
        f"from {right_name} import RIGHT\nLEFT = 'left'\n",
    )
    _write_source(
        tmp_path / f"{right_name}.py",
        f"from {left_name} import LEFT\nRIGHT = 'right'\n",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        with pytest.raises(ImportError, match="partially initialized module"):
            importlib.import_module(left_name)
    finally:
        _remove_modules(left_name)
        _remove_modules(right_name)

    # 将共享常量移到第三个无依赖模块、把依赖反转为函数参数，通常比依赖导入
    # 顺序修补循环更可靠。


def test_main_guard_distinguishes_import_from_script_execution(tmp_path, monkeypatch):
    """导入时 ``__name__`` 是模块名，以 ``__main__`` 运行时才进入脚本分支。"""

    module_name = "polyglot_main_guard_example"
    module_path = tmp_path / f"{module_name}.py"
    _write_source(
        module_path,
        'MODE = "imported"\nif __name__ == "__main__":\n    MODE = "script"\n',
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        imported = importlib.import_module(module_name)
        script_namespace = runpy.run_path(str(module_path), run_name="__main__")

        assert imported.MODE == "imported"
        assert imported.__name__ == module_name
        assert script_namespace["MODE"] == "script"
        assert script_namespace["__name__"] == "__main__"
        assert imported.MODE == "imported"
    finally:
        _remove_modules(module_name)
