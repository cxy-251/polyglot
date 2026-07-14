"""346｜selector 注册表的查询、修改、注销与关闭顺序。

modify 会原子地替换 events/data 并返回新的 SelectorKey；旧 key 是 named tuple 快照，不会随注册表
改变。unregister 返回移除前的 key，缺失时抛 KeyError。文件对象必须在 close 前注销，因为 close
后 fileno() 通常变成 -1，selector 无法再由该对象找回原注册项。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.selectors.BaseSelector.modify
# polyglot-covers: python.selectors.modify-returns-new-key
# polyglot-covers: python.selectors.BaseSelector.unregister
# polyglot-covers: python.selectors.unregister-returns-key
# polyglot-covers: python.selectors.unregister-missing-keyerror
# polyglot-covers: python.selectors.BaseSelector.get_key
# polyglot-covers: python.selectors.get-key-missing-keyerror
# polyglot-covers: python.selectors.BaseSelector.get_map
# polyglot-covers: python.selectors.selector-map-fd-keyed
# polyglot-covers: python.selectors.timeout-nonpositive-poll
# polyglot-covers: python.selectors.unregister-before-close-trap
# polyglot-covers: python.selectors.BaseSelector.close
# polyglot-covers: python.selectors.context-manager

import selectors
import socket

import pytest


def test_modify_replaces_an_immutable_key_and_map_tracks_the_current_key():
    owned, peer = socket.socketpair()
    selector = selectors.DefaultSelector()
    try:
        old_key = selector.register(owned, selectors.EVENT_READ, data="reader")
        assert selector.get_key(owned) is old_key
        assert selector.get_map()[owned.fileno()] is old_key

        new_key = selector.modify(owned, selectors.EVENT_WRITE, data="writer")
        assert new_key is not old_key
        assert old_key.events == selectors.EVENT_READ
        assert old_key.data == "reader"
        assert new_key.events == selectors.EVENT_WRITE
        assert new_key.data == "writer"
        assert selector.get_key(owned) is new_key
        assert selector.get_map()[owned.fileno()] is new_key

        # timeout <= 0 都表示轮询；可写 socket 应立即出现。
        assert selector.select(-1)[0] == (new_key, selectors.EVENT_WRITE)
        removed = selector.unregister(owned)
        assert removed is new_key
        assert len(selector.get_map()) == 0
        with pytest.raises(KeyError):
            selector.get_key(owned)
        with pytest.raises(KeyError):
            selector.unregister(owned)
    finally:
        selector.close()
        owned.close()
        peer.close()


def test_registered_file_object_must_be_unregistered_before_it_is_closed():
    owned, peer = socket.socketpair()
    selector = selectors.DefaultSelector()
    try:
        key = selector.register(owned, selectors.EVENT_READ)
        original_fd = key.fd
        owned.close()
        assert owned.fileno() == -1
        with pytest.raises(ValueError):
            selector.unregister(owned)

        # 故障恢复时仍可用先前保存的整数 fd 删除映射，但正常代码不应依赖这条补救路径。
        assert selector.unregister(original_fd) == key
    finally:
        selector.close()
        owned.close()
        peer.close()
