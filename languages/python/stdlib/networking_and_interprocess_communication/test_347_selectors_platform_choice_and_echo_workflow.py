"""347｜selector 平台选择、控制 fd 与一个非阻塞回显工作流。

DefaultSelector 在导入时选择当前平台最高效的实现；可移植代码应面向统一接口，而不是假定 Linux
epoll。底层带独立控制 fd 的 selector 还公开 fileno。第二个案例用 key.data 保存连接状态，并在
读阶段后用 modify 切换到写阶段，展示小型事件循环的核心结构。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.selectors.SelectSelector
# polyglot-covers: python.selectors.PollSelector
# polyglot-covers: python.selectors.EpollSelector
# polyglot-covers: python.selectors.default-selector-best-implementation
# polyglot-covers: python.selectors.EpollSelector.fileno
# polyglot-covers: python.selectors.selector-control-fd-noninheritable
# polyglot-covers: python.selectors.nonblocking-state-machine-workflow
# polyglot-covers: python.selectors.key-data-connection-state
# polyglot-covers: python.selectors.modify-read-to-write-interest
# polyglot-covers: python.selectors.event-mask-bit-test

import os
import selectors
import socket
import sys

import pytest


def test_concrete_selectors_offer_the_same_portable_readiness_contract():
    selector_types = [selectors.SelectSelector]
    if hasattr(selectors, "PollSelector"):
        selector_types.append(selectors.PollSelector)
    if hasattr(selectors, "EpollSelector"):
        selector_types.append(selectors.EpollSelector)

    for selector_type in selector_types:
        owned, peer = socket.socketpair()
        with selector_type() as selector:
            try:
                key = selector.register(owned, selectors.EVENT_READ, selector_type.__name__)
                peer.sendall(b"x")
                ready_key, mask = selector.select(0)[0]
                assert ready_key == key
                assert ready_key.data == selector_type.__name__
                assert mask & selectors.EVENT_READ
                assert owned.recv(1) == b"x"
                selector.unregister(owned)
            finally:
                owned.close()
                peer.close()


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or not hasattr(selectors, "EpollSelector"),
    reason="Linux 上 DefaultSelector 才应选择 epoll",
)
def test_linux_default_selector_uses_a_noninheritable_epoll_control_fd():
    with selectors.DefaultSelector() as selector:
        assert isinstance(selector, selectors.EpollSelector)
        assert selector.fileno() >= 0
        assert os.get_inheritable(selector.fileno()) is False


def test_key_data_and_modify_form_a_small_read_then_write_state_machine():
    server, client = socket.socketpair()
    server.setblocking(False)
    client.setblocking(False)
    state = {"phase": "read", "outgoing": b""}
    with selectors.DefaultSelector() as selector:
        try:
            selector.register(server, selectors.EVENT_READ, state)
            client.sendall(b"hello")

            key, mask = selector.select(0)[0]
            if mask & selectors.EVENT_READ:
                key.data["outgoing"] = server.recv(1024).upper()
                key.data["phase"] = "write"
                selector.modify(server, selectors.EVENT_WRITE, key.data)

            key, mask = selector.select(0)[0]
            if mask & selectors.EVENT_WRITE:
                sent = server.send(key.data["outgoing"])
                key.data["outgoing"] = key.data["outgoing"][sent:]
            assert key.data == {"phase": "write", "outgoing": b""}
            assert client.recv(1024) == b"HELLO"
            selector.unregister(server)
        finally:
            server.close()
            client.close()
