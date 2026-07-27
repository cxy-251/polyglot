"""导入绑定、别名与可变导出对象。

共同问题：导入后读取的是源绑定还是本地值；共享对象的内部修改是否可见；
重新绑定与修改对象为何产生不同迁移结果。
"""

# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/python/language/test_018_imports_modules_and_packages.py

import importlib
import sys

import pytest


@pytest.fixture
def clean_binding_module():
    sys.modules.pop("polyglot_binding_fixture", None)
    yield
    sys.modules.pop("polyglot_binding_fixture", None)


def test_from_import_snapshots_binding_but_shared_mutable_object_remains_aliased(
    tmp_path,
    monkeypatch,
    clean_binding_module,
):
    source = (
        "value = 1\n"
        "items = []\n"
        "def update():\n"
        "    global value\n"
        "    value = 2\n"
        "    items.append('updated')\n"
    )
    (tmp_path / "polyglot_binding_fixture.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    module = importlib.import_module("polyglot_binding_fixture")
    imported_value = module.value
    imported_items = module.items

    module.update()

    assert module.value == 2
    assert imported_value == 1
    assert imported_items is module.items
    assert imported_items == ["updated"]

    # from-import 的本地名称不是 JavaScript live binding；但若快照值本身是可变对象，
    # 两个名称仍指向同一对象。重新绑定与原地修改必须分开理解。
