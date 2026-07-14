"""159｜Linux ``memfd_create`` 与 ``eventfd`` descriptor 工作流。

``memfd`` 是没有普通 pathname 的匿名内存文件；``eventfd`` 是 kernel 维护的
64-bit counter，常用于线程/进程或 event loop 通知。二者都返回普通 fd，必须
关闭，且 Python 创建的 descriptor 默认不可跨 exec 继承。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.memfd-create python.os.MFD_CLOEXEC
# polyglot-covers: python.os.memory-file-descriptor python.os.memfd-no-pathname
# polyglot-covers: python.os.eventfd python.os.eventfd-read python.os.eventfd-write
# polyglot-covers: python.os.EFD_CLOEXEC python.os.EFD_NONBLOCK
# polyglot-covers: python.os.EFD_SEMAPHORE python.os.eventfd-counter-reset
# polyglot-covers: python.os.eventfd-semaphore-decrement python.os.eventfd-would-block

import os

import pytest


@pytest.mark.skipif(not hasattr(os, "memfd_create"), reason="host 不提供 Linux memfd")
def test_memfd_behaves_like_an_anonymous_seekable_file():
    """name 只用于诊断，不创建目录项；fd 仍支持常规 read/write/seek。"""

    fd = os.memfd_create("polyglot-example", os.MFD_CLOEXEC)
    try:
        assert os.get_inheritable(fd) is False
        assert os.write(fd, b"in-memory") == 9
        assert os.lseek(fd, 0, os.SEEK_SET) == 0
        assert os.read(fd, 20) == b"in-memory"
        assert os.fstat(fd).st_size == 9
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "eventfd"), reason="host 不提供 Linux eventfd")
def test_eventfd_read_returns_counter_and_resets_it_to_zero():
    """非 semaphore 模式一次读出累计值；zero counter 的 nonblocking read 会失败。"""

    fd = os.eventfd(2, os.EFD_CLOEXEC | os.EFD_NONBLOCK)
    try:
        assert os.get_inheritable(fd) is False
        os.eventfd_write(fd, 3)
        assert os.eventfd_read(fd) == 5
        with pytest.raises(BlockingIOError):
            os.eventfd_read(fd)
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "eventfd"), reason="host 不提供 Linux eventfd")
def test_eventfd_semaphore_mode_returns_one_and_decrements_counter():
    """EFD_SEMAPHORE 把 counter 当 permit count，而不是一次清零的累计通知。"""

    flags = os.EFD_CLOEXEC | os.EFD_NONBLOCK | os.EFD_SEMAPHORE
    fd = os.eventfd(2, flags)
    try:
        assert os.eventfd_read(fd) == 1
        assert os.eventfd_read(fd) == 1
        with pytest.raises(BlockingIOError):
            os.eventfd_read(fd)
    finally:
        os.close(fd)
