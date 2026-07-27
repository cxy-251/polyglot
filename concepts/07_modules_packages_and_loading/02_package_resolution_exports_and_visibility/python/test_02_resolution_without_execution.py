"""解析、执行与相对基准。

共同问题：定位模块是否等于执行模块；相对说明符由什么上下文解释；
导出列表或命名约定是否构成真正访问控制。
"""

# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/python/language/test_018_imports_modules_and_packages.py

import importlib
import importlib.util
import sys

import pytest


@pytest.fixture
def clean_resolution_module():
    sys.modules.pop("polyglot_resolution_fixture", None)
    yield
    sys.modules.pop("polyglot_resolution_fixture", None)


def test_find_spec_locates_a_module_without_executing_its_body(
    tmp_path,
    monkeypatch,
    clean_resolution_module,
):
    marker = tmp_path / "executed.txt"
    source = f"from pathlib import Path\nPath({str(marker)!r}).write_text('yes')\n"
    (tmp_path / "polyglot_resolution_fixture.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    spec = importlib.util.find_spec("polyglot_resolution_fixture")

    assert spec is not None
    assert spec.origin == str(tmp_path / "polyglot_resolution_fixture.py")
    assert not marker.exists()

    importlib.import_module("polyglot_resolution_fixture")
    assert marker.read_text(encoding="utf-8") == "yes"


def test_relative_import_requires_an_explicit_package_context():
    with pytest.raises(TypeError, match="package"):
        importlib.import_module(".core")

    # 源码中的 from . import core 使用当前模块 __package__；运行期 import_module
    # 必须显式传入 package，不能按进程 cwd 猜测相对基准。
