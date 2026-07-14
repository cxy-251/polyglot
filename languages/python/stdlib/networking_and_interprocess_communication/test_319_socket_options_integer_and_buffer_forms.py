"""319｜getsockopt/setsockopt 的 integer 与 native buffer 两种表示。

不带 buflen 的 getsockopt 假定 integer option；带 buflen 返回原始 bytes，调用者按平台 C ABI
用 struct 解码。setsockopt 接收 int 或 bytes-like；kernel 可能调整 buffer size，所以不能把
SO_SNDBUF 的读回值写死为请求值。选项 level/optname 必须使用对应 SOL_*/SO_* 常量。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import socket
import struct


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
