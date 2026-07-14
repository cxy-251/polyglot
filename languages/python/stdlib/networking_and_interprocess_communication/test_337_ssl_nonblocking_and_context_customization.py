"""337｜non-blocking SSLSocket retry 与 SSLContext wrapper class/configuration hooks。

普通 socket 的 EAGAIN 在 TLS 层变成 SSLWantRead/Write；操作方向和所需底层 readiness 可能相反，
必须按异常等待对应 fd 后重试完整调用。sslsocket_class/sslobject_class 允许 framework 插入子类。
keylog_filename 仅用于调试且会泄露 session secrets；生产环境不能随意启用或提交其输出。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.nonblocking-ssl-want-read-write-not-blockingioerror
# polyglot-covers: python.ssl.nonblocking-ssl-operation-direction-may-reverse
# polyglot-covers: python.ssl.nonblocking-ssl-retry-whole-operation
# polyglot-covers: python.ssl.SSLContext.sslsocket_class
# polyglot-covers: python.ssl.SSLContext.sslobject_class
# polyglot-covers: python.ssl.custom-ssl-wrapper-subclasses
# polyglot-covers: python.ssl.SSLContext.session_stats
# polyglot-covers: python.ssl.SSLContext.set_ecdh_curve
# polyglot-covers: python.ssl.HAS_ECDH
# polyglot-covers: python.ssl.HAS_ALPN
# polyglot-covers: python.ssl.SSLContext.num_tickets
# polyglot-covers: python.ssl.SSLContext.post_handshake_auth
# polyglot-covers: python.ssl.SSLContext.hostname_checks_common_name
# polyglot-covers: python.ssl.SSLContext.keylog_filename
# polyglot-covers: python.ssl.keylog-debug-secret-leak-trap

import socket
import ssl

import pytest

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM


class CustomSSLSocket(ssl.SSLSocket):
    pass


class CustomSSLObject(ssl.SSLObject):
    pass


def test_nonblocking_handshake_reports_tls_readiness_not_blockingioerror():
    client_raw, idle_peer = socket.socketpair()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cadata=CERTIFICATE_PEM)
    client = context.wrap_socket(
        client_raw,
        server_hostname="localhost",
        do_handshake_on_connect=False,
    )
    client.setblocking(False)
    try:
        with pytest.raises(ssl.SSLWantReadError):
            client.do_handshake()
    finally:
        client.close()
        idle_peer.close()


def test_context_can_select_custom_socket_and_memory_wrapper_classes():
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.sslsocket_class = CustomSSLSocket
    owned, peer = socket.socketpair()
    wrapped = server_context.wrap_socket(
        owned,
        server_side=True,
        do_handshake_on_connect=False,
    )
    try:
        assert isinstance(wrapped, CustomSSLSocket)
    finally:
        wrapped.close()
        peer.close()

    client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_context.sslobject_class = CustomSSLObject
    ssl_object = client_context.wrap_bio(
        ssl.MemoryBIO(),
        ssl.MemoryBIO(),
        server_hostname="localhost",
    )
    assert isinstance(ssl_object, CustomSSLObject)


def test_context_exposes_session_tls13_and_hostname_policy_controls(tmp_path):
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.num_tickets = 1
    server.post_handshake_auth = True
    if ssl.HAS_ECDH:
        assert server.set_ecdh_curve("prime256v1") is None

    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client.hostname_checks_common_name = False
    client.keylog_filename = str(tmp_path / "tls-secrets.log")

    assert server.num_tickets == 1
    assert server.post_handshake_auth is True
    assert client.hostname_checks_common_name is False
    assert client.keylog_filename == str(tmp_path / "tls-secrets.log")
    assert isinstance(ssl.HAS_ECDH, bool)
    assert isinstance(ssl.HAS_ALPN, bool)

    stats = server.session_stats()
    assert {"number", "connect", "hits", "misses", "timeouts"} <= stats.keys()
    assert all(isinstance(value, int) for value in stats.values())
