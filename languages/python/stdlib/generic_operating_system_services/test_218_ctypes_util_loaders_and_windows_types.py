"""218｜``ctypes.util`` library discovery、loader objects 与 Windows type surface。

``find_library`` 返回可交给 loader 的平台相关名称，不保证是绝对路径。LibraryLoader
只是按指定 DLL type 建 object 的便利 facade；calling convention 仍由 CDLL/PyDLL/
WinDLL 等 class 决定。``ctypes.wintypes`` 可导入 type declarations，但 Windows ABI
调用与 WinDLL/OleDLL loaders 只应在 Windows 分支使用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.util python.ctypes.util.find_library
# polyglot-covers: python.ctypes.find-library-platform-name
# polyglot-covers: python.ctypes.LibraryLoader
# polyglot-covers: python.ctypes.LibraryLoader-index
# polyglot-covers: python.ctypes.predefined-library-loaders
# polyglot-covers: python.ctypes.pydll-loader
# polyglot-covers: python.ctypes.DEFAULT_MODE python.ctypes.RTLD_GLOBAL
# polyglot-covers: python.ctypes.RTLD_LOCAL
# polyglot-covers: python.ctypes.wintypes python.ctypes.wintypes.POINT
# polyglot-covers: python.ctypes.wintypes.RECT python.ctypes.wintypes.HANDLE
# polyglot-covers: python.ctypes.WinDLL-platform-availability
# polyglot-covers: python.ctypes.OleDLL-platform-availability
# polyglot-covers: python.ctypes.windll-platform-availability
# polyglot-covers: python.ctypes.oledll-platform-availability

import ctypes
import ctypes.util
from ctypes import wintypes
import os

import pytest


def _c_library_name():
    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")
    return name


def test_find_library_result_is_loader_input_not_required_absolute_path():
    """只要求结果可加载；Linux 常见 soname、macOS path 与 Windows 名称格式都不同。"""

    name = _c_library_name()
    library = ctypes.CDLL(name, mode=ctypes.DEFAULT_MODE)

    assert isinstance(name, str)
    assert name
    assert isinstance(library, ctypes.CDLL)
    assert ctypes.util.find_library("polyglot_library_that_cannot_exist_7f3a") is None


def test_libraryloader_supports_explicit_load_and_index_syntax():
    """两次访问创建两个 Python library wrappers；native loader 可在底层复用 handle。"""

    name = _c_library_name()
    loader = ctypes.LibraryLoader(ctypes.CDLL)
    explicit = loader.LoadLibrary(name)
    indexed = loader[name]

    assert isinstance(explicit, ctypes.CDLL)
    assert isinstance(indexed, ctypes.CDLL)
    assert explicit is not indexed
    assert isinstance(ctypes.cdll, ctypes.LibraryLoader)
    assert isinstance(ctypes.pydll, ctypes.LibraryLoader)


def test_loader_mode_constants_are_integer_platform_configuration():
    """常量值由平台决定；跨平台代码不应假设 RTLD_GLOBAL 的具体 bit pattern。"""

    assert isinstance(ctypes.DEFAULT_MODE, int)
    assert isinstance(ctypes.RTLD_GLOBAL, int)
    assert isinstance(ctypes.RTLD_LOCAL, int)


def test_wintypes_structures_preserve_declared_field_workflow():
    """可在任意平台学习 shape；只有 Windows 上的 size/calling convention 才是目标 ABI。"""

    point = wintypes.POINT(x=3, y=4)
    rectangle = wintypes.RECT(left=1, top=2, right=11, bottom=22)
    null_handle = wintypes.HANDLE()

    assert (point.x, point.y) == (3, 4)
    assert (rectangle.right - rectangle.left) == 10
    assert (rectangle.bottom - rectangle.top) == 20
    assert null_handle.value is None


def test_windows_calling_convention_loaders_are_platform_conditional():
    """在 module scope 无条件引用 WinDLL/windll 会让 POSIX import 直接失败。"""

    expected = os.name == "nt"

    for name in ("WinDLL", "OleDLL", "windll", "oledll"):
        assert hasattr(ctypes, name) is expected
