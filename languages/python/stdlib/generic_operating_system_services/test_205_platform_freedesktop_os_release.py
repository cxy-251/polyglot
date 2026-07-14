"""205｜``platform.freedesktop_os_release`` parsing、candidate fallback 与 cache。

Python 3.10 新增的 os-release reader 会解引号/反斜杠，保证 NAME、ID、PRETTY_NAME
三个基础字段，并返回 dict copy。它缓存首次成功解析；测试替换内部 candidate path 指向
``tmp_path``，既执行真实 public parser，又不读取或修改宿主机 ``/etc/os-release``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.platform.freedesktop_os_release
# polyglot-covers: python.platform.os-release-candidate-order
# polyglot-covers: python.platform.os-release-shell-unquoting
# polyglot-covers: python.platform.os-release-required-defaults
# polyglot-covers: python.platform.os-release-vendor-fields
# polyglot-covers: python.platform.os-release-ID_LIKE-workflow
# polyglot-covers: python.platform.os-release-cache
# polyglot-covers: python.platform.os-release-copy-on-return
# polyglot-covers: python.platform.os-release-missing-error

import platform

import pytest


def _redirect_candidates(monkeypatch, *paths):
    monkeypatch.setattr(platform, "_os_release_candidates", tuple(map(str, paths)))
    monkeypatch.setattr(platform, "_os_release_cache", None)


def test_os_release_uses_first_readable_candidate_and_unquotes_values(
    tmp_path,
    monkeypatch,
):
    """ID/ID_LIKE 用于程序判断；PRETTY_NAME 等展示字段不适合稳定比较。"""

    missing = tmp_path / "missing-os-release"
    release_file = tmp_path / "os-release"
    release_file.write_text(
        """\
# ignored comment
NAME="Example Linux"
ID=example
PRETTY_NAME="Example Linux \\"Stable\\""
VERSION_ID="1.0"
ID_LIKE="debian rhel"
VENDOR_FIELD="cost=\\$0"
""",
        encoding="utf-8",
    )
    _redirect_candidates(monkeypatch, missing, release_file)

    info = platform.freedesktop_os_release()

    assert info["NAME"] == "Example Linux"
    assert info["ID"] == "example"
    assert info["PRETTY_NAME"] == 'Example Linux "Stable"'
    assert info["VERSION_ID"] == "1.0"
    assert [info["ID"], *info["ID_LIKE"].split()] == [
        "example",
        "debian",
        "rhel",
    ]
    assert info["VENDOR_FIELD"] == "cost=$0"


def test_os_release_returns_copies_and_caches_first_success(tmp_path, monkeypatch):
    """修改返回 dict 不污染 cache；磁盘变化也需新进程或显式失效内部 cache 才可见。"""

    release_file = tmp_path / "os-release"
    release_file.write_text("ID=first\n", encoding="utf-8")
    _redirect_candidates(monkeypatch, release_file)

    first = platform.freedesktop_os_release()
    first["ID"] = "mutated-by-caller"
    release_file.write_text("ID=second\n", encoding="utf-8")
    cached = platform.freedesktop_os_release()

    assert cached["ID"] == "first"
    assert cached["NAME"] == "Linux"
    assert cached["PRETTY_NAME"] == "Linux"
    assert first is not cached

    platform._os_release_cache = None
    assert platform.freedesktop_os_release()["ID"] == "second"


def test_os_release_raises_when_no_candidate_is_readable(tmp_path, monkeypatch):
    """缺少 os-release 是可预期平台差异，调用方可捕获 OSError 再选择其他识别方法。"""

    first = tmp_path / "absent-one"
    second = tmp_path / "absent-two"
    _redirect_candidates(monkeypatch, first, second)

    with pytest.raises(OSError):
        platform.freedesktop_os_release()
