"""失败初始化、缓存状态与重试。

共同问题：初始化失败的模块是否留在缓存；同一键再次加载是否重新执行；
循环依赖为何可能只看到部分初始化状态。
"""

# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/python/language/test_018_imports_modules_and_packages.py

import importlib
import sys

import pytest


@pytest.fixture
def clean_failing_module():
    sys.modules.pop("polyglot_failing_import", None)
    yield
    sys.modules.pop("polyglot_failing_import", None)


def test_failed_import_is_removed_from_sys_modules_and_a_retry_reexecutes(
    tmp_path,
    monkeypatch,
    clean_failing_module,
):
    marker = tmp_path / "runs.txt"
    source = (
        "from pathlib import Path\n"
        f"_marker = Path({str(marker)!r})\n"
        "_marker.write_text(_marker.read_text() + 'run\\n' if _marker.exists() else 'run\\n')\n"
        "raise RuntimeError('initialization failed')\n"
    )
    (tmp_path / "polyglot_failing_import.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    for expected_runs in [1, 2]:
        with pytest.raises(RuntimeError, match="initialization failed"):
            importlib.import_module("polyglot_failing_import")

        assert "polyglot_failing_import" not in sys.modules
        assert marker.read_text(encoding="utf-8").splitlines() == ["run"] * expected_runs

    # Python 在执行前暂放 module object 以支持循环；执行失败会删除本次缓存项，因此相同
    # 名称重试会重新执行。依赖方仍可能保留失败期间取得的外部对象引用。
