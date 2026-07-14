"""344｜epoll 控制 fd 的生命周期、复制与失效 fd 错误。

epoll 对象自身也是一个可轮询、默认不可继承的文件描述符，并支持上下文管理器。fromfd 接管给定
控制 fd 的所有权，并不会自动 dup；若两个 Python 对象包装同一个 fd，任意一方 close 都会让另一方
失效。本例先 os.dup，明确分离所有权。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.select.epoll.context-manager
# polyglot-covers: python.select.epoll.close
# polyglot-covers: python.select.epoll.closed
# polyglot-covers: python.select.epoll.fileno
# polyglot-covers: python.select.epoll-control-fd-noninheritable
# polyglot-covers: python.select.epoll.fromfd
# polyglot-covers: python.select.epoll.fromfd-ownership-trap
# polyglot-covers: python.select.epoll.unregister-closed-fd-ebadf

import errno
import os
import select
import socket

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(select, "epoll"),
    reason="epoll 是 Linux 专用接口",
)


def test_epoll_is_a_noninheritable_context_managed_file_descriptor():
    epoll = select.epoll()
    control_fd = epoll.fileno()
    assert control_fd >= 0
    assert os.get_inheritable(control_fd) is False
    assert epoll.closed is False

    with epoll as entered:
        assert entered is epoll
    assert epoll.closed is True
    with pytest.raises(ValueError):
        epoll.fileno()


def test_fromfd_wraps_the_given_descriptor_so_callers_should_dup_first():
    original = select.epoll()
    duplicate_fd = os.dup(original.fileno())
    clone = select.epoll.fromfd(duplicate_fd)
    try:
        assert clone.fileno() == duplicate_fd
        assert clone.fileno() != original.fileno()
        clone.close()
        # 关闭 duplicate 的 wrapper 不影响原控制 fd。
        assert original.closed is False
        assert original.poll(0) == []
    finally:
        clone.close()
        original.close()


def test_unregistering_an_already_closed_watched_fd_reports_ebadf():
    epoll = select.epoll()
    owned, peer = socket.socketpair()
    watched_fd = owned.fileno()
    try:
        epoll.register(watched_fd, select.EPOLLIN)
        owned.close()
        # Python 3.9 起不再吞掉内核的 EBADF；正确顺序是先 unregister，再 close watched fd。
        with pytest.raises(OSError) as raised:
            epoll.unregister(watched_fd)
        assert raised.value.errno == errno.EBADF
    finally:
        owned.close()
        peer.close()
        epoll.close()
