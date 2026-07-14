"""216｜``ctypes`` ``use_errno``、private errno copy 与 thread-local state。

声明 ``use_errno=True`` 后，ctypes 会在 foreign call 前后与真实 C errno 交换一份
thread-local copy，调用方再用 ``get_errno`` 读取。这避免另一个 C call 提前覆盖错误码，
但仍必须紧跟返回值协议判断；errno 非零本身不代表本次调用失败。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ctypes.get_errno python.ctypes.set_errno
# polyglot-covers: python.ctypes.set-errno-returns-previous
# polyglot-covers: python.ctypes.errno-thread-local
# polyglot-covers: python.ctypes.CDLL-use_errno
# polyglot-covers: python.ctypes.foreign-call-errno-capture
# polyglot-covers: python.ctypes.errno-return-value-first
# polyglot-covers: python.ctypes.get_last_error-platform-availability
# polyglot-covers: python.ctypes.set_last_error-platform-availability

import ctypes
import ctypes.util
import errno
import os
import queue
import threading

import pytest


def test_set_errno_returns_previous_value_and_state_is_thread_local():
    """worker 修改自己的 private copy，不会覆盖 main thread 已设置的 EINVAL。"""

    original = ctypes.get_errno()
    result_queue = queue.Queue()

    def worker():
        initial = ctypes.get_errno()
        previous = ctypes.set_errno(errno.EBUSY)
        result_queue.put((initial, previous, ctypes.get_errno()))

    try:
        assert ctypes.set_errno(errno.EINVAL) == original
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        initial, previous, current = result_queue.get_nowait()
        assert (initial, previous, current) == (0, 0, errno.EBUSY)
        assert ctypes.get_errno() == errno.EINVAL
    finally:
        ctypes.set_errno(original)


@pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX libc close")
def test_use_errno_captures_close_failure_immediately_after_foreign_call():
    """-1 先表明失败，EBADF 才解释原因；案例只关闭必然无效的负 fd。"""

    name = ctypes.util.find_library("c")
    if name is None:
        pytest.skip("当前平台未找到 C runtime")

    library = ctypes.CDLL(name, use_errno=True)
    close = library["close"]
    close.restype = ctypes.c_int
    close.argtypes = [ctypes.c_int]
    original = ctypes.get_errno()

    try:
        ctypes.set_errno(0)
        result = close(-1)

        assert result == -1
        assert ctypes.get_errno() == errno.EBADF
    finally:
        ctypes.set_errno(original)


def test_windows_last_error_helpers_are_exposed_only_on_windows():
    """不要在跨平台 module import 阶段无条件引用仅 Windows 提供的 helper。"""

    expected = os.name == "nt"

    assert hasattr(ctypes, "get_last_error") is expected
    assert hasattr(ctypes, "set_last_error") is expected
