"""204｜``platform`` architecture、system alias 与 OS-specific probe fallback。

``architecture`` 可能调用系统 ``file`` 命令，只是 executable 格式的启发式结果；判断
当前解释器位数时 ``sys.maxsize`` 更可靠。OS-specific 函数在其他系统通常返回调用方
提供的 fallback 或空字段，适合展示信息而非能力检测。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.platform.architecture python.platform.architecture-fallback
# polyglot-covers: python.platform.architecture-file-command-caveat
# polyglot-covers: python.platform.system_alias python.platform.SunOS-Solaris-alias
# polyglot-covers: python.platform.libc_ver
# polyglot-covers: python.platform.java_ver python.platform.win32_ver
# polyglot-covers: python.platform.win32_edition python.platform.win32_is_iot
# polyglot-covers: python.platform.mac_ver
# polyglot-covers: python.platform.platform-specific-empty-fields

import platform
import sys


def test_architecture_returns_strings_and_agrees_with_pointer_size_indicator():
    """linkage 可为空；bits 对当前解释器通常来自 executable probe 或 pointer size。"""

    bits, linkage = platform.architecture()
    pointer_bits = "64bit" if sys.maxsize > 2**32 else "32bit"

    assert bits in ("32bit", "64bit")
    assert bits == pointer_bits
    assert isinstance(linkage, str)


def test_system_alias_maps_sunos_release_to_common_solaris_numbering():
    """SunOS 5.x 的 marketing alias 是 Solaris 2.x；未知 system 保持不变。"""

    assert platform.system_alias("SunOS", "5.11", "Generic") == (
        "Solaris",
        "2.11",
        "Generic",
    )
    assert platform.system_alias("ExampleOS", "1.2", "build") == (
        "ExampleOS",
        "1.2",
        "build",
    )


def test_libc_probe_returns_caller_fallback_when_file_cannot_be_scanned(tmp_path):
    """不存在的 executable 不抛错，而是返回给定 lib/version fallback。"""

    missing = tmp_path / "missing-executable"

    assert platform.libc_ver(
        executable=str(missing),
        lib="unknown-libc",
        version="unknown-version",
    ) == ("unknown-libc", "unknown-version")


def test_platform_specific_probes_keep_documented_tuple_shapes():
    """不要把空字段当作否定能力；它只表示当前实现无法取得识别信息。"""

    java = platform.java_ver()
    windows = platform.win32_ver()
    mac = platform.mac_ver()

    assert len(java) == 4
    assert len(java[2]) == 3
    assert len(java[3]) == 3
    assert len(windows) == 4
    assert len(mac) == 3
    assert len(mac[1]) == 3


def test_windows_edition_helpers_have_explicit_non_windows_fallback():
    """edition 返回 None 表示无法取得；IoT predicate 相应为 False。"""

    if platform.system() != "Windows":
        assert platform.win32_edition() is None
        assert platform.win32_is_iot() is False
