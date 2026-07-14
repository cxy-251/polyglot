"""312｜blocking、non-blocking、timeout 三种模式及共享 fd 状态陷阱。

setblocking(True/False) 分别等价于 settimeout(None/0.0)；正 timeout 是第三种模式。底层实现会把
timeout socket 设为 OS non-blocking。dup 的 Python wrapper 各自保存 timeout 值，却共享同一
open file description 的 OS blocking flag，因此一个 wrapper 改模式可让另一个出现意外 EAGAIN。
setdefaulttimeout 是进程级默认值，测试必须恢复，避免影响以后创建的 socket。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.setblocking
# polyglot-covers: python.socket.socket.getblocking
# polyglot-covers: python.socket.socket.settimeout
# polyglot-covers: python.socket.socket.gettimeout
# polyglot-covers: python.socket.blocking-mode-timeout-none
# polyglot-covers: python.socket.nonblocking-mode-timeout-zero
# polyglot-covers: python.socket.timeout-mode-positive-value
# polyglot-covers: python.socket.timeout-mode-os-nonblocking
# polyglot-covers: python.socket.duplicate-fd-shares-os-blocking-state
# polyglot-covers: python.socket.duplicate-wrapper-timeout-metadata-can-diverge
# polyglot-covers: python.socket.setdefaulttimeout
# polyglot-covers: python.socket.getdefaulttimeout
# polyglot-covers: python.socket.default-timeout-new-sockets-only
# polyglot-covers: python.socket.timeout
# polyglot-covers: python.socket.timeout-alias-TimeoutError-3.10

import socket

import pytest


def test_setblocking_and_settimeout_are_two_views_of_the_same_mode():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.setblocking(False)
        assert sock.getblocking() is False
        assert sock.gettimeout() == 0.0

        sock.setblocking(True)
        assert sock.getblocking() is True
        assert sock.gettimeout() is None

        sock.settimeout(0.25)
        assert sock.getblocking() is True
        assert sock.gettimeout() == 0.25

        with pytest.raises(ValueError):
            sock.settimeout(-1)
    finally:
        sock.close()


def test_duplicate_wrappers_can_disagree_with_shared_os_nonblocking_flag():
    left, right = socket.socketpair()
    duplicate = left.dup()
    try:
        assert duplicate.gettimeout() is None
        left.setblocking(False)

        # duplicate 的 Python timeout metadata 没变，但 dup fd 共享 OS O_NONBLOCK 状态，
        # 所以看似 blocking 的 duplicate 在无数据时仍立即得到 BlockingIOError。
        assert duplicate.getblocking() is True
        with pytest.raises(BlockingIOError):
            duplicate.recv(1)
    finally:
        duplicate.close()
        left.close()
        right.close()


def test_process_default_timeout_applies_only_to_sockets_created_after_change():
    previous = socket.getdefaulttimeout()
    before = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    created = None
    try:
        socket.setdefaulttimeout(0.5)
        created = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        assert before.gettimeout() == previous
        assert created.gettimeout() == 0.5
        assert socket.timeout is TimeoutError
    finally:
        socket.setdefaulttimeout(previous)
        before.close()
        if created is not None:
            created.close()
