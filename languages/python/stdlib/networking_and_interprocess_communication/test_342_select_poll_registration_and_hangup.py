"""342｜poll 的注册表、事件位掩码与 hangup。

poll 用整数事件位组合表达兴趣和结果。重复 register 同一个 fd 等价于修改其掩码，而不是创建
第二份订阅；unregister 未注册对象则抛 KeyError。POLLHUP/POLLERR 等错误位可能在没有显式订阅
时仍由内核返回，所以实际循环不能只比较 ``mask == POLLIN``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.select.poll
# polyglot-covers: python.select.poll.register
# polyglot-covers: python.select.poll.register-again-modifies
# polyglot-covers: python.select.poll.modify
# polyglot-covers: python.select.poll.unregister
# polyglot-covers: python.select.poll.unregister-missing-keyerror
# polyglot-covers: python.select.poll.timeout-milliseconds
# polyglot-covers: python.select.POLLIN
# polyglot-covers: python.select.POLLOUT
# polyglot-covers: python.select.POLLHUP
# polyglot-covers: python.select.poll-event-bitmask-trap

import os
import select
import socket

import pytest


def _events_by_fd(events):
    return {fd: mask for fd, mask in events}


def test_register_again_replaces_the_interest_mask_and_modify_updates_it():
    owned, peer = socket.socketpair()
    poller = select.poll()
    try:
        poller.register(owned, select.POLLIN)
        # 再次注册相同 fd 不会产生重复结果；这里将兴趣改成永远较容易满足的 POLLOUT。
        poller.register(owned, select.POLLOUT)
        events = _events_by_fd(poller.poll(0))
        assert events[owned.fileno()] & select.POLLOUT
        assert not events[owned.fileno()] & select.POLLIN

        peer.sendall(b"x")
        poller.modify(owned, select.POLLIN)
        events = _events_by_fd(poller.poll(0))
        assert events[owned.fileno()] & select.POLLIN
        assert owned.recv(1) == b"x"

        poller.unregister(owned)
        assert poller.poll(0) == []
        with pytest.raises(KeyError):
            poller.unregister(owned)
    finally:
        owned.close()
        peer.close()


def test_poll_hangup_is_a_bit_that_must_be_tested_independently():
    read_fd, write_fd = os.pipe()
    poller = select.poll()
    try:
        poller.register(read_fd, select.POLLIN)
        os.write(write_fd, b"last")
        os.close(write_fd)
        write_fd = -1

        mask = _events_by_fd(poller.poll(0))[read_fd]
        # 数据和 EOF 可以同时到达，因此 POLLIN 与 POLLHUP 并不互斥。
        assert mask & select.POLLIN
        assert mask & select.POLLHUP
        assert os.read(read_fd, 4) == b"last"
        assert os.read(read_fd, 1) == b""
    finally:
        poller.unregister(read_fd)
        os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)
