"""340｜SSLSession 注入与 TLS 1.2 session resumption。

同一个 client context 可把首次 handshake 的 SSLSession 传给后续 wrap_bio；server context 必须
保持相同，才能命中其 session cache。TLS 1.3 ticket 在 handshake 后异步到达，演示更复杂；本例
固定 TLS 1.2，使 session ID 在 handshake 完成时即可复用。session 不能跨不同 SSLContext 使用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.wrap-bio-session-parameter
# polyglot-covers: python.ssl.ssl-session-client-injection-before-handshake
# polyglot-covers: python.ssl.ssl-session-same-context-required
# polyglot-covers: python.ssl.ssl-session-server-cache
# polyglot-covers: python.ssl.ssl-session-tls12-id-resumption
# polyglot-covers: python.ssl.ssl-session-tls13-ticket-arrives-post-handshake
# polyglot-covers: python.ssl.session_reused
# polyglot-covers: python.ssl.session-stats-cache-hit

import ssl

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate
from test_334_ssl_memory_bio_handshake_and_data import MemoryTLSPair


def test_tls12_session_can_be_reused_by_a_second_connection(tmp_path):
    certificate, private_key = write_test_certificate(tmp_path)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate, private_key)
    server_context.maximum_version = ssl.TLSVersion.TLSv1_2
    client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_context.load_verify_locations(cadata=CERTIFICATE_PEM)
    client_context.maximum_version = ssl.TLSVersion.TLSv1_2

    first = MemoryTLSPair(client_context, server_context)
    first.handshake()
    session = first.client.session
    assert session.id
    assert first.client.session_reused is False

    second = MemoryTLSPair(
        client_context,
        server_context,
        session=session,
    )
    second.handshake()
    assert second.client.session_reused is True
    assert second.server.session_reused is True
    assert server_context.session_stats()["hits"] >= 1
