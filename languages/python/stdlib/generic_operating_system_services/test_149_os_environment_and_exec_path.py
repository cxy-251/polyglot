"""149｜``os.environ``/``environb``、getenv、putenv trap 与 executable PATH。

``os.environ`` 是导入时捕获、与 C environment 同步的 mutable mapping。应修改
这个 mapping，而不是直接调用 ``putenv``：后者会影响 future child process，却不会
反向更新 Python mapping。Unix 的 ``environb`` 与 text view 双向同步，并使用
filesystem codec。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.environ python.os.environment-mapping
# polyglot-covers: python.os.getenv python.os.environment-default
# polyglot-covers: python.os.environment-set-delete python.os.environment-process-global
# polyglot-covers: python.os.environment-merge python.os.environment-update-merge
# polyglot-covers: python.os.putenv python.os.putenv-mapping-trap
# polyglot-covers: python.os.unsetenv python.os.environb
# polyglot-covers: python.os.getenvb python.os.supports-bytes-environ
# polyglot-covers: python.os.text-bytes-environ-sync python.os.get-exec-path
# polyglot-covers: python.os.PATH python.os.pathsep

import os

import pytest


def test_environ_mutation_is_visible_to_getenv_and_deletion_removes_it(monkeypatch):
    """修改 mapping 会自动调用 putenv/unsetenv；fixture 负责恢复全局状态。"""

    key = "POLYGLOT_OS_ENVIRON_CASE"
    monkeypatch.setitem(os.environ, key, "中文-value")

    assert os.environ[key] == "中文-value"
    assert os.getenv(key) == "中文-value"
    assert os.getenv("POLYGLOT_DEFINITELY_MISSING", "fallback") == "fallback"

    monkeypatch.delitem(os.environ, key)
    assert os.getenv(key) is None


def test_environ_merge_returns_copy_while_inplace_merge_updates_process():
    """PEP 584 的 | 不修改左侧；|= 会通过 _Environ 写入真实 process environment。"""

    key = "POLYGLOT_OS_ENVIRON_MERGE"
    merged = os.environ | {key: "copy-only"}

    assert merged[key] == "copy-only"
    assert key not in os.environ

    try:
        os.environ |= {key: "process-value"}
        assert os.getenv(key) == "process-value"
    finally:
        # 直接 |= 不在 monkeypatch 的 mutation log 中，所以本案例自己清理。
        os.environ.pop(key, None)


def test_direct_putenv_does_not_update_python_mapping():
    """getenv 读取 os.environ，而非 C environment；这是直接 putenv 的常见陷阱。"""

    key = "POLYGLOT_OS_DIRECT_PUTENV"
    os.environ.pop(key, None)
    os.putenv(key, "c-environment-only")
    try:
        assert key not in os.environ
        assert os.getenv(key) is None
    finally:
        os.unsetenv(key)


@pytest.mark.skipif(not os.supports_bytes_environ, reason="平台没有 bytes environment")
def test_environb_and_environ_are_synchronized_views(monkeypatch):
    """Unix bytes view 可无损表达非 text protocol；ASCII 案例展示双向同步。"""

    bytes_key = b"POLYGLOT_OS_BYTES_ENV"
    monkeypatch.setitem(os.environb, bytes_key, b"raw-value")

    assert os.getenvb(bytes_key) == b"raw-value"
    assert os.environ[bytes_key.decode()] == "raw-value"

    os.environ[bytes_key.decode()] = "changed"
    assert os.environb[bytes_key] == b"changed"


def test_get_exec_path_splits_explicit_path_without_searching_filesystem():
    """返回 search directories；空 component 也保留，shell 将其视作 current dir。"""

    supplied = os.pathsep.join(["/opt/tools", "", "/usr/local/bin"])

    assert os.get_exec_path({"PATH": supplied}) == [
        "/opt/tools",
        "",
        "/usr/local/bin",
    ]
    assert os.get_exec_path({}) == os.defpath.split(os.pathsep)


@pytest.mark.skipif(not os.supports_bytes_environ, reason="bytes PATH 只在部分平台存在")
def test_get_exec_path_rejects_ambiguous_text_and_bytes_path_keys():
    """env 同时给 'PATH' 与 b'PATH' 时没有可靠优先级，因此显式报 ValueError。"""

    with pytest.raises(ValueError, match="PATH"):
        os.get_exec_path({"PATH": "/text", b"PATH": b"/bytes"})
