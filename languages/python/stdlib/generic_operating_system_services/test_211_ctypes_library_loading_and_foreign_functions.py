"""211｜``ctypes`` dynamic library loading、foreign function 与 signature。

``CDLL`` 加载采用 cdecl calling convention 的共享库；``CDLL(None)`` 表示当前进程的
全局符号空间。函数默认返回 ``c_int``，实际调用前应声明 ``restype`` 和 ``argtypes``，
否则 pointer-sized 返回值可能被截断，错误的参数也可能直到 native code 中才暴露。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.CDLL python.ctypes.CDLL-none
# polyglot-covers: python.ctypes.CDLL-name python.ctypes.CDLL-handle
# polyglot-covers: python.ctypes.cdll python.ctypes.LibraryLoader.LoadLibrary
# polyglot-covers: python.ctypes.shared-library-load-error
# polyglot-covers: python.ctypes.foreign-function-attribute-cache
# polyglot-covers: python.ctypes.foreign-function-index-fresh-wrapper
# polyglot-covers: python.ctypes.foreign-function-default-restype
# polyglot-covers: python.ctypes.foreign-function-restype
# polyglot-covers: python.ctypes.foreign-function-argtypes
# polyglot-covers: python.ctypes.ArgumentError python.ctypes.c-string-nul-semantics

import ctypes
import ctypes.util

import pytest


def _load_c_library():
    """Docker 目标是 POSIX；极简平台若找不到 libc 名称则明确跳过依赖符号的案例。"""

    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("ctypes.util.find_library('c') 未找到 C runtime")
    return name, ctypes.CDLL(name)


def test_cdll_loads_named_library_and_none_opens_current_process():
    """handle 是 native loader handle；只检查其结构，不依赖平台具体数值。"""

    name, library = _load_c_library()
    current_process = ctypes.CDLL(None)
    loaded_by_factory = ctypes.cdll.LoadLibrary(name)

    assert library._name == name
    assert isinstance(library._handle, int)
    assert current_process._name is None
    assert isinstance(current_process._handle, int)
    assert isinstance(loaded_by_factory, ctypes.CDLL)


def test_missing_shared_library_raises_oserror(tmp_path):
    """加载失败来自操作系统 dynamic loader，不会返回 false-like library object。"""

    missing = tmp_path / "lib_polyglot_definitely_missing.so"

    with pytest.raises(OSError):
        ctypes.CDLL(str(missing))


def test_function_attribute_lookup_is_cached_but_index_lookup_is_fresh():
    """fresh wrapper 适合为同一 native symbol 配置互不干扰的不同 signature。"""

    _, library = _load_c_library()

    assert library.strlen is library.strlen
    assert library["strlen"] is not library["strlen"]


def test_declared_strlen_signature_converts_bytes_and_rejects_text():
    """c_char_p 接收 bytes；C strlen 在首个 NUL 停止，而 Python len 会计入后缀。"""

    _, library = _load_c_library()
    strlen = library["strlen"]

    assert strlen.restype is ctypes.c_int
    assert strlen.argtypes is None

    strlen.restype = ctypes.c_size_t
    strlen.argtypes = [ctypes.c_char_p]

    assert strlen(b"hello") == 5
    assert strlen(b"ab\x00ignored") == 2
    with pytest.raises(ctypes.ArgumentError):
        strlen("hello")
