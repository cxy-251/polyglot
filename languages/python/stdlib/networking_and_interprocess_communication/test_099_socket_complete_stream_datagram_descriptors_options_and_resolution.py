"""099｜socket 构造参数、IntEnum 常量、原子 flags 与资源上下文。

family/type/proto 决定地址表示和传输语义；AF_* 与 SOCK_* 是 IntEnum，仍可传给 C 风格 API。
新 socket 默认 blocking、不可继承。Linux 可把 SOCK_NONBLOCK/SOCK_CLOEXEC 原子并入 type，
但 Python 的 socket.type 会清除这两个 flag，只保留基本 kind，不能用它判断当前 blocking 状态。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket
# polyglot-covers: python.socket.socket-family-type-proto
# polyglot-covers: python.socket.socket.family
# polyglot-covers: python.socket.socket.type
# polyglot-covers: python.socket.socket.proto
# polyglot-covers: python.socket.AddressFamily
# polyglot-covers: python.socket.SocketKind
# polyglot-covers: python.socket.SocketType
# polyglot-covers: python.socket.AF_UNIX
# polyglot-covers: python.socket.SOCK_STREAM
# polyglot-covers: python.socket.SOCK_DGRAM
# polyglot-covers: python.socket.SOCK_NONBLOCK
# polyglot-covers: python.socket.SOCK_CLOEXEC
# polyglot-covers: python.socket.atomic-socket-flags-cleared-from-type
# polyglot-covers: python.socket.new-socket-blocking-default
# polyglot-covers: python.socket.new-socket-non-inheritable
# polyglot-covers: python.socket.socket-context-manager-close
# polyglot-covers: python.socket.socketpair
# polyglot-covers: python.socket.socketpair-connected



import enum
import socket
import pytest
import os
import struct
import sys

def test_constructor_attributes_are_int_enums_and_context_manager_closes():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        assert isinstance(sock.family, socket.AddressFamily)
        assert isinstance(sock.family, enum.IntEnum)
        assert isinstance(sock.type, socket.SocketKind)
        assert sock.family == socket.AF_UNIX
        assert sock.type == socket.SOCK_STREAM
        assert sock.proto == 0
        assert isinstance(sock, socket.SocketType)
        assert sock.getblocking() is True
        assert sock.get_inheritable() is False
        descriptor = sock.fileno()
        assert descriptor >= 0

    assert sock.fileno() == -1


def test_socketpair_returns_connected_non_inheritable_endpoints():
    left, right = socket.socketpair()
    try:
        assert left.family == right.family
        assert left.type == right.type == socket.SOCK_STREAM
        assert left.get_inheritable() is False
        assert right.get_inheritable() is False
        assert left.send(b"x") == 1
        assert right.recv(1) == b"x"
    finally:
        left.close()
        right.close()


def test_atomic_nonblocking_flag_changes_mode_but_not_type_attribute():
    kind = socket.SOCK_STREAM | socket.SOCK_NONBLOCK | socket.SOCK_CLOEXEC
    sock = socket.socket(socket.AF_UNIX, kind)
    try:
        assert sock.type == socket.SOCK_STREAM
        assert sock.getblocking() is False
        assert sock.get_inheritable() is False
    finally:
        sock.close()


# blocking、non-blocking、timeout 三种模式及共享 fd 状态陷阱。
#
# setblocking(True/False) 分别等价于 settimeout(None/0.0)；正 timeout 是第三种模式。底层实现会把
# timeout socket 设为 OS non-blocking。dup 的 Python wrapper 各自保存 timeout 值，却共享同一
# open file description 的 OS blocking flag，因此一个 wrapper 改模式可让另一个出现意外 EAGAIN。
# setdefaulttimeout 是进程级默认值，测试必须恢复，避免影响以后创建的 socket。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# stream socket 的 send/recv、sendall、peek、half-close 与 EOF。
#
# stream 没有消息边界：recv(bufsize) 最多返回 bufsize，调用者必须循环组帧。send 返回实际写入
# 数量，可能小于输入；sendall 负责循环但成功只返回 None，失败也无法报告已发送量。SHUT_WR
# 发送 EOF 同时保留读取方向；对端把 recv 返回 b"" 解释为有序 EOF，而不是一条空消息。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.send
# polyglot-covers: python.socket.send-may-be-partial
# polyglot-covers: python.socket.send-caller-retries-remainder
# polyglot-covers: python.socket.socket.sendall
# polyglot-covers: python.socket.sendall-none-on-success
# polyglot-covers: python.socket.sendall-error-progress-unknown
# polyglot-covers: python.socket.socket.recv
# polyglot-covers: python.socket.recv-up-to-bufsize
# polyglot-covers: python.socket.stream-has-no-message-boundaries
# polyglot-covers: python.socket.MSG_PEEK
# polyglot-covers: python.socket.recv-peek-does-not-consume
# polyglot-covers: python.socket.socket.shutdown
# polyglot-covers: python.socket.SHUT_WR
# polyglot-covers: python.socket.stream-half-close
# polyglot-covers: python.socket.recv-empty-bytes-is-eof
# polyglot-covers: python.socket.socket-has-no-read-write-methods



def test_sendall_and_recv_require_application_level_framing():
    left, right = socket.socketpair()
    try:
        assert left.sendall(b"abcdef") is None
        assert right.recv(2, socket.MSG_PEEK) == b"ab"
        assert right.recv(2) == b"ab"
        assert right.recv(4) == b"cdef"

        # 小 payload 通常一次 send 完成，但正确代码仍使用返回值切掉已发送前缀。
        payload = memoryview(b"reply")
        while payload:
            sent = right.send(payload)
            payload = payload[sent:]
        assert left.recv(16) == b"reply"
    finally:
        left.close()
        right.close()


def test_shutdown_write_delivers_eof_without_disabling_receive_direction():
    left, right = socket.socketpair()
    try:
        left.sendall(b"last")
        left.shutdown(socket.SHUT_WR)
        assert right.recv(16) == b"last"
        assert right.recv(16) == b""

        right.sendall(b"reverse still works")
        assert left.recv(64) == b"reverse still works"
        assert not hasattr(left, "read")
        assert not hasattr(left, "write")
    finally:
        left.close()
        right.close()


# recv_into 把数据直接写入 caller-owned writable buffer。
#
# recv 创建新 bytes；recv_into 改写 bytearray/memoryview 并返回写入计数，适合复用缓冲区。nbytes
# 省略或为 0 时最多填满传入 view；只应读取计数覆盖的区域，未写入部分保留旧内容。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.recv_into
# polyglot-covers: python.socket.recv-into-writable-buffer
# polyglot-covers: python.socket.recv-into-memoryview-slice
# polyglot-covers: python.socket.recv-into-return-count
# polyglot-covers: python.socket.recv-into-zero-means-buffer-size
# polyglot-covers: python.socket.recv-into-unwritten-region-preserved



def test_recv_into_writes_only_the_selected_memoryview_slice():
    left, right = socket.socketpair()
    buffer = bytearray(b"..........")
    try:
        left.sendall(b"data")
        count = right.recv_into(memoryview(buffer)[3:7])

        assert count == 4
        assert buffer == bytearray(b"...data...")
    finally:
        left.close()
        right.close()


def test_zero_nbytes_uses_the_destination_buffer_length():
    left, right = socket.socketpair()
    buffer = bytearray(b"------")
    try:
        left.sendall(b"abc")
        left.shutdown(socket.SHUT_WR)
        count = right.recv_into(buffer, 0)

        assert count == 3
        assert buffer == bytearray(b"abc---")
    finally:
        left.close()
        right.close()


# AF_UNIX datagram 的 sendto/recvfrom、消息边界和 recvfrom_into。
#
# 未 connect 的 datagram socket 每次 sendto 指定目标，recvfrom 同时返回完整消息和发送方地址。
# 消息超过 bufsize 会被截断而非留给下一次读取。pathname 地址是 str；案例全部放在 pytest 临时
# 目录，不使用网络接口。recvfrom_into 可直接写 caller buffer，并同样返回来源地址。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.bind
# polyglot-covers: python.socket.AF_UNIX-pathname-address-str
# polyglot-covers: python.socket.socket.sendto
# polyglot-covers: python.socket.sendto-unconnected-destination
# polyglot-covers: python.socket.socket.recvfrom
# polyglot-covers: python.socket.recvfrom-data-address-pair
# polyglot-covers: python.socket.datagram-preserves-message-boundaries
# polyglot-covers: python.socket.datagram-truncation-discards-remainder
# polyglot-covers: python.socket.socket.recvfrom_into
# polyglot-covers: python.socket.recvfrom-into-count-and-address



def test_sendto_and_recvfrom_preserve_separate_datagrams_and_source_address(tmp_path):
    sender_path = tmp_path / "sender.sock"
    receiver_path = tmp_path / "receiver.sock"
    sender = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sender.bind(str(sender_path))
        receiver.bind(str(receiver_path))
        assert sender.sendto(b"first", str(receiver_path)) == 5
        assert sender.sendto(b"second", str(receiver_path)) == 6

        first, first_address = receiver.recvfrom(64)
        second, second_address = receiver.recvfrom(64)
        assert (first, second) == (b"first", b"second")
        assert first_address == second_address == str(sender_path)
    finally:
        sender.close()
        receiver.close()


def test_small_datagram_buffer_discards_remainder_and_into_returns_address(tmp_path):
    sender_path = tmp_path / "sender-into.sock"
    receiver_path = tmp_path / "receiver-into.sock"
    sender = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    buffer = bytearray(b"........")
    try:
        sender.bind(str(sender_path))
        receiver.bind(str(receiver_path))
        sender.sendto(b"too-long", str(receiver_path))
        assert receiver.recvfrom(3)[0] == b"too"

        sender.sendto(b"next", str(receiver_path))
        count, address = receiver.recvfrom_into(memoryview(buffer)[2:6])
        assert count == 4
        assert address == str(sender_path)
        assert buffer == bytearray(b"..next..")
    finally:
        sender.close()
        receiver.close()


# Unix stream server 的 socket-bind-listen-accept 与 client connect/connect_ex。
#
# 监听 socket 只负责 accept；数据必须在 accept 返回的新 conn 上收发。connect_ex 把 C connect
# 的 errno 改为返回值，成功为 0，适合非阻塞状态机；名称解析等前置错误仍可能抛异常。accept
# 产生的新 socket 默认不可继承，且在默认 timeout 为 None 时由 blocking listener 接受为 blocking。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.server-socket-bind-listen-accept-sequence
# polyglot-covers: python.socket.socket.listen
# polyglot-covers: python.socket.listen-default-backlog
# polyglot-covers: python.socket.socket.connect
# polyglot-covers: python.socket.socket.connect_ex
# polyglot-covers: python.socket.connect-ex-zero-success
# polyglot-covers: python.socket.socket.accept
# polyglot-covers: python.socket.accept-connection-address-pair
# polyglot-covers: python.socket.accept-data-on-connection-not-listener
# polyglot-covers: python.socket.accepted-socket-non-inheritable
# polyglot-covers: python.socket.accepted-socket-blocking-normalization
# polyglot-covers: python.socket.accepted-socket-inherits-global-default-timeout
# polyglot-covers: python.socket.socket.getsockname
# polyglot-covers: python.socket.socket.getpeername



def test_listener_accepts_a_distinct_connected_socket_and_echoes(tmp_path):
    path = tmp_path / "server.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    accepted = None
    try:
        listener.bind(str(path))
        listener.listen()
        assert listener.getsockname() == str(path)

        assert client.connect_ex(str(path)) == 0
        accepted, peer_address = listener.accept()
        assert peer_address == ""
        assert accepted is not listener
        assert accepted.get_inheritable() is False
        assert accepted.getblocking() is True
        assert accepted.getpeername() == ""

        client.sendall(b"hello")
        assert accepted.recv(64) == b"hello"
        accepted.sendall(b"HELLO")
        assert client.recv(64) == b"HELLO"
    finally:
        if accepted is not None:
            accepted.close()
        client.close()
        listener.close()


def test_connect_and_accept_use_global_default_timeout_for_new_sockets(tmp_path):
    previous = socket.getdefaulttimeout()
    listener = None
    client = None
    accepted = None
    try:
        socket.setdefaulttimeout(0.5)
        path = tmp_path / "timeout-server.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
        listener.listen()

        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        assert client.connect(str(path)) is None
        accepted, _ = listener.accept()
        assert client.gettimeout() == 0.5
        assert accepted.gettimeout() == 0.5
    finally:
        socket.setdefaulttimeout(previous)
        if accepted is not None:
            accepted.close()
        if client is not None:
            client.close()
        if listener is not None:
            listener.close()


# socket.makefile 的 buffering、文本 newline 与共享关闭所有权。
#
# makefile 把 stream socket 包成 file object，参数大体遵循 open。它要求 blocking socket；timeout
# 期间失败可能让内部 buffer 不一致。关闭 file 不会单独关闭原 socket；反过来 socket.close 后，
# 只要 makefile wrapper 仍存活，底层 fd 也暂缓关闭，直到所有 wrapper 一起关闭。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.makefile
# polyglot-covers: python.socket.makefile-open-like-mode-buffering
# polyglot-covers: python.socket.makefile-requires-blocking-socket
# polyglot-covers: python.socket.makefile-timeout-buffer-inconsistency-trap
# polyglot-covers: python.socket.makefile-text-encoding
# polyglot-covers: python.socket.makefile-universal-newlines
# polyglot-covers: python.socket.makefile-close-does-not-close-socket-alone
# polyglot-covers: python.socket.socket-close-deferred-by-makefile



def test_text_makefile_decodes_and_normalizes_newlines():
    left, right = socket.socketpair()
    reader = left.makefile("r", encoding="utf-8", newline=None)
    try:
        right.sendall("第一行\r\n第二行\n".encode())
        right.shutdown(socket.SHUT_WR)
        assert reader.readlines() == ["第一行\n", "第二行\n"]

        reader.close()
        assert left.fileno() >= 0
        left.sendall(b"socket still owns its descriptor")
        assert right.recv(64) == b"socket still owns its descriptor"
    finally:
        reader.close()
        left.close()
        right.close()


def test_open_makefile_keeps_descriptor_alive_after_socket_object_closes():
    left, right = socket.socketpair()
    binary_reader = left.makefile("rb", buffering=0)
    left.close()
    try:
        assert left.fileno() == -1
        right.sendall(b"data")
        assert binary_reader.read(4) == b"data"
    finally:
        binary_reader.close()
        right.close()


# socket fd 的 dup、fromfd、detach、fileno= 与显式 close 所有权。
#
# dup/fromfd 复制 descriptor，两个 wrapper 可独立 close；detach 则把同一个 descriptor 的所有权
# 移出原对象，原 socket 立即进入 closed 状态。socket.socket(fileno=fd) 接管同一 fd，不再复制；
# 若仍由其他代码 close 会产生 double-close 风险。socket.close(fd) 是跨平台关闭 socket fd 的入口。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.fileno
# polyglot-covers: python.socket.socket.dup
# polyglot-covers: python.socket.dup-new-non-inheritable-descriptor
# polyglot-covers: python.socket.fromfd
# polyglot-covers: python.socket.fromfd-duplicates-descriptor
# polyglot-covers: python.socket.socket.detach
# polyglot-covers: python.socket.detach-original-wrapper-closed
# polyglot-covers: python.socket.socket-fileno-constructor
# polyglot-covers: python.socket.fileno-constructor-same-descriptor-ownership
# polyglot-covers: python.socket.fileno-constructor-auto-detect
# polyglot-covers: python.socket.close-fd
# polyglot-covers: python.socket.socket.set_inheritable
# polyglot-covers: python.socket.socket.get_inheritable




def test_dup_and_fromfd_create_independently_closable_descriptors():
    left, right = socket.socketpair()
    duplicate = left.dup()
    from_fd = socket.fromfd(left.fileno(), left.family, left.type, left.proto)
    original_fd = left.fileno()
    try:
        assert duplicate.fileno() != original_fd
        assert from_fd.fileno() not in (original_fd, duplicate.fileno())
        assert duplicate.get_inheritable() is False
        assert from_fd.get_inheritable() is False

        left.close()
        duplicate.sendall(b"dup")
        assert right.recv(3) == b"dup"
        from_fd.sendall(b"fromfd")
        assert right.recv(6) == b"fromfd"
    finally:
        left.close()
        duplicate.close()
        from_fd.close()
        right.close()


def test_detach_and_fileno_constructor_transfer_the_same_descriptor():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    descriptor = sock.detach()
    assert sock.fileno() == -1

    adopted = socket.socket(fileno=descriptor)
    try:
        assert adopted.fileno() == descriptor
        assert adopted.family == socket.AF_UNIX
        assert adopted.type == socket.SOCK_STREAM
        adopted.set_inheritable(True)
        assert adopted.get_inheritable() is True
        adopted.set_inheritable(False)
        assert adopted.get_inheritable() is False
    finally:
        adopted.close()

    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_module_close_releases_a_detached_socket_descriptor():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    descriptor = sock.detach()
    socket.close(descriptor)

    with pytest.raises(OSError):
        os.fstat(descriptor)


# getsockopt/setsockopt 的 integer 与 native buffer 两种表示。
#
# 不带 buflen 的 getsockopt 假定 integer option；带 buflen 返回原始 bytes，调用者按平台 C ABI
# 用 struct 解码。setsockopt 接收 int 或 bytes-like；kernel 可能调整 buffer size，所以不能把
# SO_SNDBUF 的读回值写死为请求值。选项 level/optname 必须使用对应 SOL_*/SO_* 常量。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.getsockopt
# polyglot-covers: python.socket.getsockopt-integer-form
# polyglot-covers: python.socket.getsockopt-buffer-form
# polyglot-covers: python.socket.getsockopt-buffer-caller-decodes-native-struct
# polyglot-covers: python.socket.socket.setsockopt
# polyglot-covers: python.socket.setsockopt-integer-form
# polyglot-covers: python.socket.setsockopt-bytes-like-form
# polyglot-covers: python.socket.SOL_SOCKET
# polyglot-covers: python.socket.SO_TYPE
# polyglot-covers: python.socket.SO_KEEPALIVE
# polyglot-covers: python.socket.SO_SNDBUF
# polyglot-covers: python.socket.kernel-may-adjust-socket-option



def test_getsockopt_returns_int_or_raw_buffer_according_to_buflen():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) == socket.SOCK_STREAM

        raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE, struct.calcsize("i"))
        assert isinstance(raw, bytes)
        assert struct.unpack("i", raw)[0] == socket.SOCK_STREAM
    finally:
        sock.close()


def test_setsockopt_accepts_int_and_native_integer_bytes():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) == 1

        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_KEEPALIVE,
            struct.pack("i", 0),
        )
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) == 0

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF) >= 8192
    finally:
        sock.close()


# blocking stream socket 的 sendfile 文件传输。
#
# sendfile 优先 os.sendfile，必要时退回 send；file 必须二进制打开，socket 必须是 blocking
# SOCK_STREAM。offset/count 决定片段，返回发送计数且更新 file position。non-blocking socket
# 明确不支持，异步程序应使用 loop.sock_sendfile 或 loop.sendfile。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.sendfile
# polyglot-covers: python.socket.sendfile-regular-binary-file
# polyglot-covers: python.socket.sendfile-stream-only
# polyglot-covers: python.socket.sendfile-offset-count
# polyglot-covers: python.socket.sendfile-return-count
# polyglot-covers: python.socket.sendfile-updates-file-position
# polyglot-covers: python.socket.sendfile-os-sendfile-preferred
# polyglot-covers: python.socket.sendfile-fallback-send
# polyglot-covers: python.socket.sendfile-nonblocking-unsupported




def test_sendfile_sends_selected_slice_and_advances_file_position(tmp_path):
    path = tmp_path / "sendfile.bin"
    path.write_bytes(b"0123456789")
    left, right = socket.socketpair()
    try:
        with path.open("rb") as file:
            sent = left.sendfile(file, offset=2, count=4)
            assert sent == 4
            assert file.tell() == 6
        assert right.recv(16) == b"2345"
    finally:
        left.close()
        right.close()


def test_sendfile_rejects_nonblocking_socket(tmp_path):
    path = tmp_path / "nonblocking.bin"
    path.write_bytes(b"data")
    left, right = socket.socketpair()
    left.setblocking(False)
    try:
        with path.open("rb") as file:
            with pytest.raises(ValueError, match="non-blocking sockets"):
                left.sendfile(file)
    finally:
        left.close()
        right.close()


# sendmsg gather write、recvmsg 四元组与 ancillary buffer sizing。
#
# sendmsg 从多个 bytes-like buffer gather 成一个消息；recvmsg 返回 data、ancdata、msg_flags、
# address。CMSG_LEN 不含尾部 padding，CMSG_SPACE 包含可移植控制消息所需 padding；接收 ancillary
# data 应优先用后者计算 ancbufsize，否则控制消息可能被截断或丢弃。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.sendmsg
# polyglot-covers: python.socket.sendmsg-gather-buffers
# polyglot-covers: python.socket.sendmsg-return-byte-count
# polyglot-covers: python.socket.socket.recvmsg
# polyglot-covers: python.socket.recvmsg-data-ancdata-flags-address
# polyglot-covers: python.socket.recvmsg-ancillary-buffer-zero-default
# polyglot-covers: python.socket.CMSG_LEN
# polyglot-covers: python.socket.CMSG_SPACE
# polyglot-covers: python.socket.cmsg-space-includes-padding
# polyglot-covers: python.socket.cmsg-space-preferred-portability
# polyglot-covers: python.socket.cmsg-length-range-overflow




def test_sendmsg_gathers_buffers_and_recvmsg_returns_four_fields():
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sent = left.sendmsg([b"head", memoryview(b"-body")])
        data, ancillary, flags, address = right.recvmsg(64)

        assert sent == 9
        assert data == b"head-body"
        assert ancillary == []
        assert flags == 0
        assert address in (None, "")
    finally:
        left.close()
        right.close()


def test_cmsg_space_includes_at_least_the_unpadded_control_length():
    payload_size = 4
    assert socket.CMSG_SPACE(payload_size) >= socket.CMSG_LEN(payload_size)
    assert socket.CMSG_LEN(payload_size) >= payload_size

    with pytest.raises(OverflowError):
        socket.CMSG_SPACE(-1)


# recvmsg_into 把普通数据 scatter 到多个 writable buffer。
#
# 它返回 (nbytes, ancdata, msg_flags, address)，并按 buffers 迭代顺序依次填充；memoryview slice
# 只暴露选中区域，外侧内容保留。系统对 iovec 数量有 SC_IOV_MAX 限制，不能把任意长列表直接
# 交给底层。只读取 nbytes 覆盖的前缀，最后一个 buffer 的其余空间仍是旧值。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.socket.recvmsg_into
# polyglot-covers: python.socket.recvmsg-into-scatter-buffers
# polyglot-covers: python.socket.recvmsg-into-memoryview-slice
# polyglot-covers: python.socket.recvmsg-into-return-four-tuple
# polyglot-covers: python.socket.recvmsg-into-nbytes-valid-prefix
# polyglot-covers: python.socket.recvmsg-into-iovec-platform-limit



def test_recvmsg_into_scatter_writes_across_selected_buffers():
    left, right = socket.socketpair()
    first = bytearray(b"----")
    middle = bytearray(b"0123456789")
    last = bytearray(b"--------------")
    try:
        left.sendall(b"Mary had a little lamb")
        nbytes, ancillary, flags, address = right.recvmsg_into(
            [first, memoryview(middle)[2:9], last]
        )

        assert nbytes == 22
        assert ancillary == []
        assert flags == 0
        assert address in (None, "")
        assert first == bytearray(b"Mary")
        assert middle == bytearray(b"01 had a 9")
        assert last == bytearray(b"little lamb---")
    finally:
        left.close()
        right.close()


# AF_UNIX SCM_RIGHTS 文件描述符传递。
#
# send_fds/recv_fds 用 ancillary data 在本机进程间传 descriptor；接收方得到新的 fd number，但它
# 引用同一 open file description，因此 file offset 也共享。收到的 fd 必须逐个显式 close，否则
# 会泄漏资源。maxfds 限制接收数量；普通 message bytes 与 fd 列表一起返回。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.send_fds
# polyglot-covers: python.socket.recv_fds
# polyglot-covers: python.socket.SCM_RIGHTS
# polyglot-covers: python.socket.file-descriptor-passing-af-unix
# polyglot-covers: python.socket.recv-fds-message-fds-flags-address
# polyglot-covers: python.socket.received-fd-new-number
# polyglot-covers: python.socket.received-fd-shares-open-file-description
# polyglot-covers: python.socket.received-fd-must-be-closed
# polyglot-covers: python.socket.recv-fds-maxfds



def test_send_fds_transfers_a_readable_descriptor_and_shared_offset(tmp_path):
    path = tmp_path / "shared.txt"
    path.write_bytes(b"abcdef")
    original_fd = os.open(path, os.O_RDONLY)
    left, right = socket.socketpair()
    received_fds = []
    try:
        assert socket.send_fds(left, [b"file"], [original_fd]) == 4
        message, received_fds, flags, address = socket.recv_fds(right, 64, 1)

        assert message == b"file"
        assert len(received_fds) == 1
        assert received_fds[0] != original_fd
        assert flags == 0
        assert address in (None, "")

        assert os.read(received_fds[0], 3) == b"abc"
        # SCM_RIGHTS 复制 fd，但共享 open file description，所以原 fd 的 offset 也前进。
        assert os.read(original_fd, 3) == b"def"
    finally:
        for descriptor in received_fds:
            os.close(descriptor)
        os.close(original_fd)
        left.close()
        right.close()


# IPv4/IPv6 文本地址与 network binary 表示转换。
#
# inet_aton/ntoa 是 IPv4-only 传统接口，aton 还可能按 libc 接受缩写形式，跨平台代码不要依赖。
# inet_pton/ntop 显式 family，适合双栈；IPv6 文本可能有多种等价写法，ntop 返回规范压缩形式。
# 这只是纯转换，不做 DNS 查询，也不验证地址是否可路由。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.inet_aton
# polyglot-covers: python.socket.inet_aton-ipv4-only
# polyglot-covers: python.socket.inet_aton-abbreviated-platform-dependent
# polyglot-covers: python.socket.inet_ntoa
# polyglot-covers: python.socket.inet_ntoa-four-byte-input
# polyglot-covers: python.socket.inet_pton
# polyglot-covers: python.socket.inet_pton-explicit-family
# polyglot-covers: python.socket.inet_pton-ipv4-ipv6
# polyglot-covers: python.socket.inet_ntop
# polyglot-covers: python.socket.inet_ntop-family-specific-length
# polyglot-covers: python.socket.ip-conversion-no-dns




def test_legacy_ipv4_conversion_round_trips_exactly_four_bytes():
    packed = socket.inet_aton("192.0.2.1")
    assert packed == b"\xc0\x00\x02\x01"
    assert socket.inet_ntoa(memoryview(packed)) == "192.0.2.1"

    with pytest.raises(OSError):
        socket.inet_ntoa(b"too short")


def test_family_explicit_conversion_supports_ipv4_and_ipv6():
    ipv4 = socket.inet_pton(socket.AF_INET, "198.51.100.7")
    ipv6 = socket.inet_pton(socket.AF_INET6, "2001:db8:0:0::1")

    assert len(ipv4) == 4
    assert len(ipv6) == 16
    assert socket.inet_ntop(socket.AF_INET, ipv4) == "198.51.100.7"
    assert socket.inet_ntop(socket.AF_INET6, ipv6) == "2001:db8::1"

    with pytest.raises(OSError):
        socket.inet_pton(socket.AF_INET, "2001:db8::1")
    with pytest.raises(ValueError):
        socket.inet_ntop(socket.AF_INET6, b"four")


# host/network 字节序与本机 protocol/service database。
#
# 网络字节序是 big-endian；hton* 从 host 转 network，ntoh* 反向，round-trip 与主机端序无关。
# getprotobyname/getservbyname/getservbyport 查询 libc 数据库，不建立连接。Python 3.10 对 16-bit
# htons/ntohs 新增明确范围检查，越过 unsigned short 不再静默截断。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.htons
# polyglot-covers: python.socket.ntohs
# polyglot-covers: python.socket.htonl
# polyglot-covers: python.socket.ntohl
# polyglot-covers: python.socket.host-network-byte-order-roundtrip
# polyglot-covers: python.socket.unsigned-16-byte-order-overflow-3.10
# polyglot-covers: python.socket.getprotobyname
# polyglot-covers: python.socket.getservbyname
# polyglot-covers: python.socket.getservbyport
# polyglot-covers: python.socket.protocol-service-tables-no-connection




def test_host_and_network_byte_order_functions_are_inverse_pairs():
    short_value = 0x1234
    long_value = 0x12345678
    assert socket.ntohs(socket.htons(short_value)) == short_value
    assert socket.htons(socket.ntohs(short_value)) == short_value
    assert socket.ntohl(socket.htonl(long_value)) == long_value
    assert socket.htonl(socket.ntohl(long_value)) == long_value

    with pytest.raises(OverflowError):
        socket.htons(1 << 16)
    with pytest.raises(OverflowError):
        socket.ntohs(1 << 16)


def test_protocol_and_service_names_map_to_standard_integer_constants():
    assert socket.getprotobyname("tcp") == socket.IPPROTO_TCP
    assert socket.getprotobyname("udp") == socket.IPPROTO_UDP
    assert socket.getservbyname("http", "tcp") == 80
    assert socket.getservbyport(80, "tcp") == "http"


# getaddrinfo/getnameinfo 的五元组与 numeric-only 安全用法。
#
# getaddrinfo 返回可直接喂给 socket constructor/connect 的 (family,type,proto,canonname,sockaddr)。
# 限制 family/type/flags 可避免得到调用者不会处理的地址。AI_NUMERICHOST/AI_NUMERICSERV 禁止
# DNS/service lookup；非 numeric 输入抛 gaierror。getnameinfo 用 NI_* 做逆向的纯数字格式化。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.getaddrinfo
# polyglot-covers: python.socket.getaddrinfo-five-tuple
# polyglot-covers: python.socket.getaddrinfo-family-type-narrowing
# polyglot-covers: python.socket.AI_NUMERICHOST
# polyglot-covers: python.socket.AI_NUMERICSERV
# polyglot-covers: python.socket.getaddrinfo-numeric-no-dns
# polyglot-covers: python.socket.getnameinfo
# polyglot-covers: python.socket.NI_NUMERICHOST
# polyglot-covers: python.socket.NI_NUMERICSERV
# polyglot-covers: python.socket.getnameinfo-numeric-no-reverse-dns
# polyglot-covers: python.socket.gaierror
# polyglot-covers: python.socket.error-alias-OSError
# polyglot-covers: python.socket.herror




def test_numeric_getaddrinfo_returns_constructor_ready_five_tuples():
    results = socket.getaddrinfo(
        "127.0.0.1",
        "443",
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        flags=socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
    )
    assert results

    for family, kind, protocol, canonical_name, address in results:
        assert family == socket.AF_INET
        assert kind == socket.SOCK_STREAM
        assert isinstance(protocol, int)
        assert canonical_name == ""
        assert address == ("127.0.0.1", 443)


def test_numeric_getnameinfo_formats_without_reverse_lookup():
    result = socket.getnameinfo(
        ("127.0.0.1", 443),
        socket.NI_NUMERICHOST | socket.NI_NUMERICSERV,
    )
    assert result == ("127.0.0.1", "443")

    with pytest.raises(socket.gaierror):
        socket.getaddrinfo(
            "not-a-numeric-address",
            80,
            flags=socket.AI_NUMERICHOST,
        )


def test_socket_exception_aliases_follow_the_oserror_hierarchy():
    assert socket.error is OSError
    assert issubclass(socket.gaierror, OSError)
    assert issubclass(socket.herror, OSError)


# hostname/FQDN 与 network interface index 的环境读取。
#
# gethostname 返回本机短名但不保证 FQDN；getfqdn 会按 reverse lookup/alias 选择带点名称，仍可能
# 退回原输入。if_nameindex 列出 (index,name)，另外两个函数可双向转换。接口集合属于运行环境，
# 案例只验证内部一致性，不把 Docker 中的具体名称或 index 写死。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.gethostname
# polyglot-covers: python.socket.gethostname-not-necessarily-fqdn
# polyglot-covers: python.socket.getfqdn
# polyglot-covers: python.socket.getfqdn-fallback
# polyglot-covers: python.socket.if_nameindex
# polyglot-covers: python.socket.if_nametoindex
# polyglot-covers: python.socket.if_indextoname
# polyglot-covers: python.socket.interface-index-name-roundtrip
# polyglot-covers: python.socket.interface-list-environment-dependent
# polyglot-covers: python.socket.has_ipv6
# polyglot-covers: python.socket.has_dualstack_ipv6




def test_hostname_is_a_nonempty_local_machine_label():
    hostname = socket.gethostname()
    assert isinstance(hostname, str) and hostname


def test_getfqdn_selects_a_dotted_primary_name_or_alias_without_network(monkeypatch):
    monkeypatch.setattr(
        socket,
        "gethostbyaddr",
        lambda _: ("short", ["alias", "host.example.test"], ["192.0.2.1"]),
    )
    assert socket.getfqdn("input") == "host.example.test"

    def unavailable(_):
        raise OSError("no resolver data")

    monkeypatch.setattr(socket, "gethostbyaddr", unavailable)
    assert socket.getfqdn("unchanged.example") == "unchanged.example"


def test_each_reported_interface_round_trips_between_name_and_index():
    interfaces = socket.if_nameindex()
    assert interfaces
    for index, name in interfaces:
        assert isinstance(index, int) and index > 0
        assert isinstance(name, str) and name
        assert socket.if_nametoindex(name) == index
        assert socket.if_indextoname(index) == name

    with pytest.raises(OSError):
        socket.if_nametoindex("polyglot-interface-does-not-exist")


def test_ip_capability_probes_return_booleans_not_configuration_guarantees():
    assert isinstance(socket.has_ipv6, bool)
    assert isinstance(socket.has_dualstack_ipv6(), bool)


# create_server/create_connection 的本地 TCP convenience workflow。
#
# create_server 完成 socket/bind/listen，create_connection 会依次尝试 getaddrinfo 结果，并可在连接前
# 设置 timeout/source_address。案例只连 127.0.0.1 的随机端口，数据不会离开当前容器网络空间。
# server 返回的监听 socket 与 accept 返回的连接 socket 仍需分别关闭。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.create_server
# polyglot-covers: python.socket.create-server-bind-listen-convenience
# polyglot-covers: python.socket.create-server-random-port-zero
# polyglot-covers: python.socket.create-server-posix-reuseaddr
# polyglot-covers: python.socket.create_connection
# polyglot-covers: python.socket.create-connection-address-attempts
# polyglot-covers: python.socket.create-connection-timeout-before-connect
# polyglot-covers: python.socket.create-connection-source-address
# polyglot-covers: python.socket.local-loopback-no-external-network
# polyglot-covers: python.socket.dualstack-ipv6-requires-af-inet6




def test_convenience_server_and_client_exchange_over_container_loopback():
    server = socket.create_server(
        ("127.0.0.1", 0),
        family=socket.AF_INET,
        backlog=1,
    )
    client = None
    accepted = None
    try:
        address = server.getsockname()
        assert address[0] == "127.0.0.1"
        assert address[1] > 0
        assert server.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 1

        client = socket.create_connection(
            address,
            timeout=1.0,
            source_address=("127.0.0.1", 0),
        )
        accepted, _ = server.accept()
        assert client.gettimeout() == 1.0
        assert client.getsockname()[0] == "127.0.0.1"

        client.sendall(b"local")
        assert accepted.recv(16) == b"local"
    finally:
        if accepted is not None:
            accepted.close()
        if client is not None:
            client.close()
        server.close()


def test_dualstack_flag_is_invalid_for_ipv4_server_family():
    with pytest.raises(ValueError):
        socket.create_server(
            ("127.0.0.1", 0),
            family=socket.AF_INET,
            dualstack_ipv6=True,
        )


# Linux abstract AF_UNIX address 的 bytes 表示。
#
# pathname Unix address 返回 str 并在文件系统留下节点；Linux abstract namespace 以首字节 NUL 的
# bytes 表示，不创建文件。应用若同时接受两种地址必须处理 str/bytes 两种类型，不能无条件做
# Path 操作。地址在 kernel namespace 中仍须唯一，本例加入当前 pid。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.AF_UNIX-abstract-address
# polyglot-covers: python.socket.abstract-unix-address-leading-nul
# polyglot-covers: python.socket.abstract-unix-address-bytes
# polyglot-covers: python.socket.abstract-unix-address-no-filesystem-node
# polyglot-covers: python.socket.unix-address-str-or-bytes-trap




_section_329_pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="abstract AF_UNIX namespace 是 Linux 特性",
)


@_section_329_pytestmark
def test_abstract_unix_address_round_trips_as_leading_nul_bytes():
    address = f"\0polyglot-{os.getpid()}-abstract".encode()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.bind(address)
        actual = sock.getsockname()
        assert isinstance(actual, bytes)
        assert actual == address
        assert actual.startswith(b"\0")
    finally:
        sock.close()


# legacy host lookup 与 IPv4-only 限制。
#
# gethostbyname 只返回一个 IPv4 string；gethostbyname_ex 返回 primary、aliases、IPv4 list；
# gethostbyaddr 可反查 IPv4/IPv6。新代码通常选 getaddrinfo，因为它保留多个 family/type 结果。
# 案例只查询 numeric loopback；容器的 localhost 来自本机 resolver database，不访问外部服务。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socket.gethostbyname
# polyglot-covers: python.socket.gethostbyname-ipv4-only
# polyglot-covers: python.socket.gethostbyname-single-address
# polyglot-covers: python.socket.gethostbyname_ex
# polyglot-covers: python.socket.gethostbyname-ex-primary-aliases-addresses
# polyglot-covers: python.socket.gethostbyaddr
# polyglot-covers: python.socket.gethostbyaddr-ipv4-ipv6
# polyglot-covers: python.socket.getaddrinfo-preferred-for-dual-stack



def test_numeric_ipv4_lookup_avoids_dns_and_exposes_legacy_shapes():
    assert socket.gethostbyname("127.0.0.1") == "127.0.0.1"

    primary, aliases, addresses = socket.gethostbyname_ex("127.0.0.1")
    assert isinstance(primary, str) and primary
    assert isinstance(aliases, list)
    assert "127.0.0.1" in addresses


def test_loopback_reverse_lookup_returns_primary_alias_and_address_lists():
    primary, aliases, addresses = socket.gethostbyaddr("127.0.0.1")
    assert isinstance(primary, str) and primary
    assert isinstance(aliases, list)
    assert "127.0.0.1" in addresses
