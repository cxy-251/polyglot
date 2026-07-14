"""343｜Linux epoll 的 level、edge 与 one-shot 触发模式。

level-triggered fd 只要仍可读就会反复报告；EPOLLET 只报告状态边沿，处理器必须把非阻塞 fd
持续读到 BlockingIOError，否则缓冲区中剩余数据可能没有新的通知。EPOLLONESHOT 报告一次后会
禁用该订阅，必须用 modify 重新 armed；它适合把同一连接交给单个 worker。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.select.epoll
# polyglot-covers: python.select.epoll.register
# polyglot-covers: python.select.epoll.modify
# polyglot-covers: python.select.epoll.unregister
# polyglot-covers: python.select.epoll.poll-timeout-seconds
# polyglot-covers: python.select.EPOLLIN
# polyglot-covers: python.select.EPOLLET
# polyglot-covers: python.select.EPOLLONESHOT
# polyglot-covers: python.select.epoll-level-triggered-repeat
# polyglot-covers: python.select.epoll-edge-triggered-drain-trap
# polyglot-covers: python.select.epoll-oneshot-rearm

import select
import socket

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(select, "epoll"),
    reason="epoll 是 Linux 专用接口",
)


def _ready_fds(epoll, timeout=0):
    return {fd: mask for fd, mask in epoll.poll(timeout)}


def test_level_trigger_repeats_while_edge_trigger_requires_a_full_drain():
    owned, peer = socket.socketpair()
    owned.setblocking(False)
    with select.epoll() as epoll:
        try:
            epoll.register(owned, select.EPOLLIN)
            peer.sendall(b"ab")
            assert _ready_fds(epoll)[owned.fileno()] & select.EPOLLIN
            # 没有读取，level-triggered poll 仍会再次报告。
            assert _ready_fds(epoll)[owned.fileno()] & select.EPOLLIN
            assert owned.recv(2) == b"ab"

            epoll.modify(owned, select.EPOLLIN | select.EPOLLET)
            peer.sendall(b"cd")
            assert _ready_fds(epoll)[owned.fileno()] & select.EPOLLIN
            # edge-triggered 不会因为旧数据仍留在缓冲区而重复产生边沿。
            assert _ready_fds(epoll) == {}
            assert owned.recv(2) == b"cd"
            with pytest.raises(BlockingIOError):
                owned.recv(1)
        finally:
            epoll.unregister(owned)
            owned.close()
            peer.close()


def test_oneshot_subscription_must_be_rearmed_with_modify():
    owned, peer = socket.socketpair()
    with select.epoll() as epoll:
        try:
            interest = select.EPOLLIN | select.EPOLLONESHOT
            epoll.register(owned, interest)
            peer.sendall(b"work")
            assert _ready_fds(epoll)[owned.fileno()] & select.EPOLLIN

            # 数据甚至还没有读取，但 one-shot 已被禁用。
            assert _ready_fds(epoll) == {}
            epoll.modify(owned, interest)
            assert _ready_fds(epoll)[owned.fileno()] & select.EPOLLIN
            assert owned.recv(4) == b"work"
        finally:
            epoll.unregister(owned)
            owned.close()
            peer.close()
