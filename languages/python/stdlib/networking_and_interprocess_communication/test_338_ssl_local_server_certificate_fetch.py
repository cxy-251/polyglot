"""338｜get_server_certificate 与 deprecated module-level wrap_socket。

get_server_certificate 是会主动连接的 convenience API；本例只连接容器内 127.0.0.1 随机端口，
获取 PEM 并可用 ca_certs 验证。module-level wrap_socket 不支持 SNI/hostname matching，且每次创建
临时 context，3.7 起已弃用；新代码必须复用显式 SSLContext。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.get_server_certificate
# polyglot-covers: python.ssl.get-server-certificate-pem
# polyglot-covers: python.ssl.get-server-certificate-timeout-3.10
# polyglot-covers: python.ssl.get-server-certificate-ca-validation
# polyglot-covers: python.ssl.get-server-certificate-active-connection
# polyglot-covers: python.ssl.wrap_socket-module-function
# polyglot-covers: python.ssl.module-wrap-socket-deprecated-3.7
# polyglot-covers: python.ssl.module-wrap-socket-no-sni-hostname-check
# polyglot-covers: python.ssl.context-wrap-socket-preferred

import concurrent.futures
import socket
import ssl

import pytest

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate


def test_get_server_certificate_fetches_and_optionally_validates_local_pem(tmp_path):
    certificate, private_key = write_test_certificate(tmp_path)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, private_key)
    listener = socket.create_server(("127.0.0.1", 0), backlog=2)
    listener.settimeout(2)

    def serve_two_handshakes():
        for _ in range(2):
            raw, _ = listener.accept()
            raw.settimeout(2)
            with context.wrap_socket(raw, server_side=True) as tls_socket:
                assert tls_socket.recv(1) == b""

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            server_done = executor.submit(serve_two_handshakes)
            fetched = ssl.get_server_certificate(listener.getsockname(), timeout=2)
            verified = ssl.get_server_certificate(
                listener.getsockname(),
                ca_certs=str(certificate),
                timeout=2,
            )
            assert server_done.result(timeout=5) is None

        expected_der = ssl.PEM_cert_to_DER_cert(CERTIFICATE_PEM)
        assert ssl.PEM_cert_to_DER_cert(fetched) == expected_der
        assert ssl.PEM_cert_to_DER_cert(verified) == expected_der
    finally:
        listener.close()


def test_module_level_wrap_socket_is_deprecated_and_creates_its_own_context():
    owned, peer = socket.socketpair()
    try:
        with pytest.deprecated_call():
            wrapped = ssl.wrap_socket(owned, do_handshake_on_connect=False)
        try:
            assert isinstance(wrapped, ssl.SSLSocket)
            assert wrapped.server_hostname is None
            assert wrapped.context.check_hostname is False
        finally:
            wrapped.close()
    finally:
        peer.close()
