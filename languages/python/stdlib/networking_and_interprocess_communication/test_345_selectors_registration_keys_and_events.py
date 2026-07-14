"""345｜selectors 的统一注册 API、SelectorKey 与业务 data。

selectors 把 select、poll、epoll 等平台接口归一为 READ/WRITE 两个兴趣位。register 返回不可变的
SelectorKey，既保存原 fileobj 和规范化 fd，也可附带任意业务 data。select 返回 ``(key, mask)``，
事件循环因此无需另外维护 fd 到连接状态的并行字典。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.selectors.DefaultSelector
# polyglot-covers: python.selectors.BaseSelector.register
# polyglot-covers: python.selectors.SelectorKey
# polyglot-covers: python.selectors.SelectorKey.fileobj
# polyglot-covers: python.selectors.SelectorKey.fd
# polyglot-covers: python.selectors.SelectorKey.events
# polyglot-covers: python.selectors.SelectorKey.data
# polyglot-covers: python.selectors.EVENT_READ
# polyglot-covers: python.selectors.EVENT_WRITE
# polyglot-covers: python.selectors.BaseSelector.select
# polyglot-covers: python.selectors.select-result-key-mask
# polyglot-covers: python.selectors.register-duplicate-keyerror
# polyglot-covers: python.selectors.register-invalid-events-valueerror

import selectors
import socket

import pytest


def test_registration_key_carries_file_identity_interest_and_business_state():
    owned, peer = socket.socketpair()
    state = {"role": "upstream", "received": 0}
    with selectors.DefaultSelector() as selector:
        try:
            key = selector.register(owned, selectors.EVENT_READ, data=state)
            assert isinstance(key, selectors.SelectorKey)
            assert key.fileobj is owned
            assert key.fd == owned.fileno()
            assert key.events == selectors.EVENT_READ
            assert key.data is state

            peer.sendall(b"abc")
            ready = selector.select(0)
            assert len(ready) == 1
            ready_key, mask = ready[0]
            assert ready_key == key
            assert mask & selectors.EVENT_READ
            state["received"] += len(owned.recv(3))
            assert ready_key.data == {"role": "upstream", "received": 3}
        finally:
            selector.unregister(owned)
            owned.close()
            peer.close()


def test_duplicate_file_and_empty_interest_are_rejected():
    owned, peer = socket.socketpair()
    with selectors.DefaultSelector() as selector:
        try:
            selector.register(owned, selectors.EVENT_READ)
            with pytest.raises(KeyError):
                selector.register(owned, selectors.EVENT_WRITE)
            with pytest.raises(ValueError):
                selector.register(peer, 0)
        finally:
            selector.unregister(owned)
            owned.close()
            peer.close()
