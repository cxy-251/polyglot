"""329｜Linux abstract AF_UNIX address 的 bytes 表示。

pathname Unix address 返回 str 并在文件系统留下节点；Linux abstract namespace 以首字节 NUL 的
bytes 表示，不创建文件。应用若同时接受两种地址必须处理 str/bytes 两种类型，不能无条件做
Path 操作。地址在 kernel namespace 中仍须唯一，本例加入当前 pid。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.AF_UNIX-abstract-address
# polyglot-covers: python.socket.abstract-unix-address-leading-nul
# polyglot-covers: python.socket.abstract-unix-address-bytes
# polyglot-covers: python.socket.abstract-unix-address-no-filesystem-node
# polyglot-covers: python.socket.unix-address-str-or-bytes-trap

import os
import socket
import sys

import pytest


pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="abstract AF_UNIX namespace 是 Linux 特性",
)


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
