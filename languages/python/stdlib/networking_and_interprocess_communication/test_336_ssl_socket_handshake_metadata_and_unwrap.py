"""336｜SSLSocket 显式 handshake、加密 I/O、metadata 与 unwrap。

wrap_socket 接管已有 SOCK_STREAM，返回与 context 绑定的 SSLSocket；do_handshake_on_connect=False
让调用者控制 handshake。两端 handshake/unwrap 都会互等 wire data，本例用线程并发推进但不访问
网络。unwrap 完成 TLS close-notify 后返回新的 plain socket，后续不能继续使用原 SSL wrapper。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.SSLContext.wrap_socket
# polyglot-covers: python.ssl.wrap-socket-stream-only
# polyglot-covers: python.ssl.wrap-socket-ownership-transfer
# polyglot-covers: python.ssl.wrap-socket-server-side
# polyglot-covers: python.ssl.wrap-socket-server-hostname-sni
# polyglot-covers: python.ssl.wrap-socket-do-handshake-on-connect-false
# polyglot-covers: python.ssl.SSLSocket
# polyglot-covers: python.ssl.SSLSocket.do_handshake
# polyglot-covers: python.ssl.SSLSocket.sendall
# polyglot-covers: python.ssl.SSLSocket.recv
# polyglot-covers: python.ssl.SSLSocket.sendfile
# polyglot-covers: python.ssl.ssl-sendfile-encrypted-falls-back-to-send
# polyglot-covers: python.ssl.ssl-socket-nonzero-flags-disallowed
# polyglot-covers: python.ssl.SSLSocket.read
# polyglot-covers: python.ssl.SSLSocket.read-into-buffer
# polyglot-covers: python.ssl.SSLSocket.write
# polyglot-covers: python.ssl.ssl-read-write-deprecated-prefer-recv-send
# polyglot-covers: python.ssl.SSLSocket.pending
# polyglot-covers: python.ssl.SSLSocket.getpeercert
# polyglot-covers: python.ssl.SSLSocket.cipher
# polyglot-covers: python.ssl.SSLSocket.shared_ciphers
# polyglot-covers: python.ssl.SSLSocket.compression
# polyglot-covers: python.ssl.SSLSocket.selected_alpn_protocol
# polyglot-covers: python.ssl.SSLSocket.version
# polyglot-covers: python.ssl.SSLSocket.context
# polyglot-covers: python.ssl.SSLSocket.server_side
# polyglot-covers: python.ssl.SSLSocket.server_hostname
# polyglot-covers: python.ssl.SSLSocket.session
# polyglot-covers: python.ssl.SSLSocket.session_reused
# polyglot-covers: python.ssl.SSLSocket.unwrap
# polyglot-covers: python.ssl.unwrap-returns-new-plain-socket

import concurrent.futures
import socket
import ssl

import pytest

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate


def _contexts(tmp_path):
    certificate, private_key = write_test_certificate(tmp_path)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate, private_key)
    server_context.set_alpn_protocols(["polyglot/1"])
    client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_context.load_verify_locations(cadata=CERTIFICATE_PEM)
    client_context.set_alpn_protocols(["polyglot/1"])
    return client_context, server_context


def _handshaken_ssl_socketpair(tmp_path):
    client_context, server_context = _contexts(tmp_path)
    client_raw, server_raw = socket.socketpair()
    client_raw.settimeout(2)
    server_raw.settimeout(2)
    server_ssl = server_context.wrap_socket(
        server_raw,
        server_side=True,
        do_handshake_on_connect=False,
    )
    client_ssl = client_context.wrap_socket(
        client_raw,
        server_hostname="localhost",
        do_handshake_on_connect=False,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        server_done = executor.submit(server_ssl.do_handshake)
        client_done = executor.submit(client_ssl.do_handshake)
        assert server_done.result(timeout=5) is None
        assert client_done.result(timeout=5) is None
    return client_ssl, server_ssl


def test_ssl_socket_exchanges_data_and_exposes_negotiated_metadata(tmp_path):
    client, server = _handshaken_ssl_socketpair(tmp_path)
    try:
        assert isinstance(client, ssl.SSLSocket)
        assert client.server_side is False
        assert server.server_side is True
        assert client.server_hostname == "localhost"
        assert server.server_hostname is None
        assert client.context.protocol == ssl.PROTOCOL_TLS_CLIENT

        assert client.sendall(b"request") is None
        assert server.recv(64) == b"request"
        assert server.write(memoryview(b"reply")) == 5
        buffer = bytearray(8)
        assert client.read(2, buffer) == 2
        assert buffer[:2] == b"re"
        assert client.pending() == 3
        assert client.read() == b"ply"

        with pytest.raises(ValueError):
            client.recv(1, socket.MSG_PEEK)

        assert client.version() in {"TLSv1.2", "TLSv1.3"}
        assert client.cipher()[2] >= 128
        assert client.compression() is None
        assert client.selected_alpn_protocol() == "polyglot/1"
        assert client.shared_ciphers() is None
        assert server.shared_ciphers()
        assert client.getpeercert()["subjectAltName"]
        assert isinstance(client.session, ssl.SSLSession)
        assert client.session_reused is False

        payload_path = tmp_path / "tls-sendfile.bin"
        payload_path.write_bytes(b"file over encrypted socket")
        with payload_path.open("rb") as file:
            assert client.sendfile(file) == 26
        assert server.recv(64) == b"file over encrypted socket"
    finally:
        client.close()
        server.close()


def test_concurrent_unwrap_returns_plain_sockets_for_further_cleartext(tmp_path):
    client, server = _handshaken_ssl_socketpair(tmp_path)
    client_plain = None
    server_plain = None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            client_done = executor.submit(client.unwrap)
            server_done = executor.submit(server.unwrap)
            client_plain = client_done.result(timeout=5)
            server_plain = server_done.result(timeout=5)

        assert isinstance(client_plain, socket.socket)
        assert isinstance(server_plain, socket.socket)
        client_plain.sendall(b"cleartext after TLS shutdown")
        assert server_plain.recv(64) == b"cleartext after TLS shutdown"
    finally:
        client.close()
        server.close()
        if client_plain is not None:
            client_plain.close()
        if server_plain is not None:
            server_plain.close()
