"""101｜select.select 的三类就绪集合与 fileno 协议。

select 不传输数据，只报告哪些对象执行下一次 read、write 或异常处理时不会阻塞。返回列表保留
调用者传入的对象，而不是把它们统一替换成整数 fd；这使带 fileno() 的轻量包装对象也能携带
应用状态。timeout=0 是一次非阻塞轮询，不代表等待到事件出现。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.select.select
# polyglot-covers: python.select.read-ready-list
# polyglot-covers: python.select.write-ready-list
# polyglot-covers: python.select.exception-ready-list
# polyglot-covers: python.select.fileno-protocol
# polyglot-covers: python.select.return-original-file-objects
# polyglot-covers: python.select.timeout-zero-poll
# polyglot-covers: python.select.empty-inputs
# polyglot-covers: python.select.PIPE_BUF



import os
import select
import socket
import pytest
import errno
import selectors
import sys

class FileDescriptorView:
    """只暴露 select 所需的最小协议，并额外保存业务标签。"""

    def __init__(self, fd, label):
        self.fd = fd
        self.label = label

    def fileno(self):
        return self.fd


def test_select_reports_original_objects_through_the_fileno_protocol():
    read_fd, write_fd = os.pipe()
    reader = FileDescriptorView(read_fd, "command-pipe")
    try:
        # 尚无数据时，零超时轮询立即返回三个空集合。
        assert select.select([reader], [], [], 0) == ([], [], [])

        os.write(write_fd, b"x")
        readable, writable, exceptional = select.select([reader], [], [reader], 0)
        assert readable == [reader]
        assert readable[0].label == "command-pipe"
        assert writable == []
        assert exceptional == []
        assert os.read(read_fd, 1) == b"x"
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_read_and_write_sets_are_independent_and_preserve_input_order():
    left, right = socket.socketpair()
    try:
        right.sendall(b"ready")
        # socket buffer 尚有空间，因此 left 可同时出现在 read 与 write 返回列表中。
        readable, writable, exceptional = select.select(
            [left, right], [right, left], [left], 0
        )
        assert readable == [left]
        assert writable == [right, left]
        assert exceptional == []
        assert left.recv(5) == b"ready"
    finally:
        left.close()
        right.close()


def test_empty_poll_and_pipe_buf_portability_contract():
    # Unix 允许空输入配合 timeout=0；非零或 None 在不同平台可能出错或永久等待，不能用它 sleep。
    assert select.select([], [], [], 0) == ([], [], [])

    # POSIX 保证向 pipe 一次写入不超过 PIPE_BUF 的数据不会和其他 writer 的写入交错。
    # 它不是 pipe 总容量，也不保证更大的 write 一定被拆开。
    assert select.PIPE_BUF >= 512


# poll 的注册表、事件位掩码与 hangup。
#
# poll 用整数事件位组合表达兴趣和结果。重复 register 同一个 fd 等价于修改其掩码，而不是创建
# 第二份订阅；unregister 未注册对象则抛 KeyError。POLLHUP/POLLERR 等错误位可能在没有显式订阅
# 时仍由内核返回，所以实际循环不能只比较 ``mask == POLLIN``。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# Linux epoll 的 level、edge 与 one-shot 触发模式。
#
# level-triggered fd 只要仍可读就会反复报告；EPOLLET 只报告状态边沿，处理器必须把非阻塞 fd
# 持续读到 BlockingIOError，否则缓冲区中剩余数据可能没有新的通知。EPOLLONESHOT 报告一次后会
# 禁用该订阅，必须用 modify 重新 armed；它适合把同一连接交给单个 worker。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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




_section_343_pytestmark = pytest.mark.skipif(
    not hasattr(select, "epoll"),
    reason="epoll 是 Linux 专用接口",
)


def _ready_fds(epoll, timeout=0):
    return {fd: mask for fd, mask in epoll.poll(timeout)}


@_section_343_pytestmark
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


@_section_343_pytestmark
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


# epoll 控制 fd 的生命周期、复制与失效 fd 错误。
#
# epoll 对象自身也是一个可轮询、默认不可继承的文件描述符，并支持上下文管理器。fromfd 接管给定
# 控制 fd 的所有权，并不会自动 dup；若两个 Python 对象包装同一个 fd，任意一方 close 都会让另一方
# 失效。本例先 os.dup，明确分离所有权。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.select.epoll.context-manager
# polyglot-covers: python.select.epoll.close
# polyglot-covers: python.select.epoll.closed
# polyglot-covers: python.select.epoll.fileno
# polyglot-covers: python.select.epoll-control-fd-noninheritable
# polyglot-covers: python.select.epoll.fromfd
# polyglot-covers: python.select.epoll.fromfd-ownership-trap
# polyglot-covers: python.select.epoll.unregister-closed-fd-ebadf




_section_344_pytestmark = pytest.mark.skipif(
    not hasattr(select, "epoll"),
    reason="epoll 是 Linux 专用接口",
)


@_section_344_pytestmark
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


@_section_344_pytestmark
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


@_section_344_pytestmark
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


# selectors 的统一注册 API、SelectorKey 与业务 data。
#
# selectors 把 select、poll、epoll 等平台接口归一为 READ/WRITE 两个兴趣位。register 返回不可变的
# SelectorKey，既保存原 fileobj 和规范化 fd，也可附带任意业务 data。select 返回 ``(key, mask)``，
# 事件循环因此无需另外维护 fd 到连接状态的并行字典。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# selector 注册表的查询、修改、注销与关闭顺序。
#
# modify 会原子地替换 events/data 并返回新的 SelectorKey；旧 key 是 named tuple 快照，不会随注册表
# 改变。unregister 返回移除前的 key，缺失时抛 KeyError。文件对象必须在 close 前注销，因为 close
# 后 fileno() 通常变成 -1，selector 无法再由该对象找回原注册项。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# selector 平台选择、控制 fd 与一个非阻塞回显工作流。
#
# DefaultSelector 在导入时选择当前平台最高效的实现；可移植代码应面向统一接口，而不是假定 Linux
# epoll。底层带独立控制 fd 的 selector 还公开 fileno。第二个案例用 key.data 保存连接状态，并在
# 读阶段后用 modify 切换到写阶段，展示小型事件循环的核心结构。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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
