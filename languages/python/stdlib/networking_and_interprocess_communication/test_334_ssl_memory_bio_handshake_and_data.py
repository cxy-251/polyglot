"""334｜MemoryBIO/SSLObject 驱动无 socket 的完整 TLS state machine。

SSLObject 只处理协议，不做 network I/O：incoming BIO 接收 wire bytes，outgoing BIO 产出待发送
bytes。framework 在每次 SSLWantRead/Write 后把数据搬到对端并按 readiness 重试。案例在内存中
完成 certificate verification、hostname check、加密 application data 和连接 metadata 查询。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.MemoryBIO
# polyglot-covers: python.ssl.MemoryBIO.pending
# polyglot-covers: python.ssl.MemoryBIO.eof
# polyglot-covers: python.ssl.MemoryBIO.read
# polyglot-covers: python.ssl.MemoryBIO.write
# polyglot-covers: python.ssl.MemoryBIO.write_eof
# polyglot-covers: python.ssl.memory-bio-write-after-eof-error
# polyglot-covers: python.ssl.SSLContext.wrap_bio
# polyglot-covers: python.ssl.SSLObject
# polyglot-covers: python.ssl.ssl-object-no-network-io
# polyglot-covers: python.ssl.ssl-object-all-io-nonblocking
# polyglot-covers: python.ssl.SSLObject.do_handshake
# polyglot-covers: python.ssl.memory-bio-handshake-pump
# polyglot-covers: python.ssl.SSLWantReadError-retry-after-input
# polyglot-covers: python.ssl.SSLWantWriteError-retry-after-output-drain
# polyglot-covers: python.ssl.SSLObject.write
# polyglot-covers: python.ssl.SSLObject.read
# polyglot-covers: python.ssl.SSLObject.pending
# polyglot-covers: python.ssl.SSLObject.getpeercert
# polyglot-covers: python.ssl.getpeercert-decoded-validated-dict
# polyglot-covers: python.ssl.getpeercert-binary-der
# polyglot-covers: python.ssl.SSLObject.cipher
# polyglot-covers: python.ssl.SSLObject.version
# polyglot-covers: python.ssl.SSLObject.compression
# polyglot-covers: python.ssl.SSLObject.get_channel_binding
# polyglot-covers: python.ssl.CHANNEL_BINDING_TYPES
# polyglot-covers: python.ssl.SSLObject.context
# polyglot-covers: python.ssl.SSLObject.server_side
# polyglot-covers: python.ssl.SSLObject.server_hostname
# polyglot-covers: python.ssl.SSLObject.session
# polyglot-covers: python.ssl.SSLObject.session_reused
# polyglot-covers: python.ssl.SSLSession
# polyglot-covers: python.ssl.SSLSession.id
# polyglot-covers: python.ssl.SSLSession.time
# polyglot-covers: python.ssl.SSLSession.timeout
# polyglot-covers: python.ssl.SSLSession.ticket_lifetime_hint
# polyglot-covers: python.ssl.SSLSession.has_ticket

import ssl

import pytest

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate


class MemoryTLSPair:
    """把两个 SSLObject 与四个 BIO 组合成可由测试显式 pump 的协议对。"""

    def __init__(
        self,
        client_context,
        server_context,
        server_hostname="localhost",
        session=None,
    ):
        self.client_in = ssl.MemoryBIO()
        self.client_out = ssl.MemoryBIO()
        self.server_in = ssl.MemoryBIO()
        self.server_out = ssl.MemoryBIO()
        self.client = client_context.wrap_bio(
            self.client_in,
            self.client_out,
            server_hostname=server_hostname,
            session=session,
        )
        self.server = server_context.wrap_bio(
            self.server_in,
            self.server_out,
            server_side=True,
        )

    @staticmethod
    def _move(source, destination):
        wire_data = source.read()
        if wire_data:
            destination.write(wire_data)
        return len(wire_data)

    def pump(self):
        return self._move(self.client_out, self.server_in) + self._move(
            self.server_out,
            self.client_in,
        )

    def handshake(self):
        client_done = False
        server_done = False
        for _ in range(20):
            if not client_done:
                try:
                    self.client.do_handshake()
                    client_done = True
                except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                    pass
            if not server_done:
                try:
                    self.server.do_handshake()
                    server_done = True
                except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                    pass
            self.pump()
            if client_done and server_done:
                return
        raise AssertionError("memory BIO TLS handshake 未在有限 pump 次数内完成")


def make_memory_tls_pair(tmp_path, server_hostname="localhost"):
    certificate, private_key = write_test_certificate(tmp_path)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate, private_key)
    client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_context.load_verify_locations(cadata=CERTIFICATE_PEM)
    return MemoryTLSPair(client_context, server_context, server_hostname)


def test_memory_bio_tracks_pending_bytes_eof_and_rejects_post_eof_write():
    bio = ssl.MemoryBIO()
    assert bio.pending == 0
    assert bio.eof is False
    assert bio.write(b"wire") == 4
    assert bio.pending == 4

    bio.write_eof()
    assert bio.eof is False
    assert bio.read(2) == b"wi"
    assert bio.read() == b"re"
    assert bio.eof is True
    with pytest.raises(ssl.SSLError):
        bio.write(b"too late")


def test_ssl_objects_handshake_verify_identity_and_exchange_application_data(tmp_path):
    pair = make_memory_tls_pair(tmp_path)
    assert isinstance(pair.client, ssl.SSLObject)
    assert pair.client.server_side is False
    assert pair.server.server_side is True
    assert pair.client.server_hostname == "localhost"

    with pytest.raises(ssl.SSLWantReadError):
        pair.client.read(1)
    pair.handshake()

    assert pair.client.write(b"request") == 7
    pair.pump()
    assert pair.server.read(7) == b"request"

    assert pair.server.write(b"reply") == 5
    pair.pump()
    assert pair.client.read(2) == b"re"
    assert pair.client.pending() == 3
    assert pair.client.read() == b"ply"


def test_negotiated_metadata_certificate_and_session_are_available_after_handshake(tmp_path):
    pair = make_memory_tls_pair(tmp_path)
    pair.handshake()

    assert pair.client.context.protocol == ssl.PROTOCOL_TLS_CLIENT
    assert pair.client.version() in {"TLSv1.2", "TLSv1.3"}
    cipher_name, protocol, secret_bits = pair.client.cipher()
    assert cipher_name
    assert protocol.startswith("TLS")
    assert secret_bits >= 128
    assert pair.client.compression() is None

    decoded = pair.client.getpeercert()
    assert ("DNS", "localhost") in decoded["subjectAltName"]
    assert pair.client.getpeercert(binary_form=True) == ssl.PEM_cert_to_DER_cert(
        CERTIFICATE_PEM
    )
    assert pair.server.getpeercert() is None

    assert "tls-unique" in ssl.CHANNEL_BINDING_TYPES
    binding = pair.client.get_channel_binding("tls-unique")
    assert binding is None or isinstance(binding, bytes)

    session = pair.client.session
    assert isinstance(session, ssl.SSLSession)
    assert isinstance(session.id, bytes)
    assert isinstance(session.time, int)
    assert isinstance(session.timeout, int)
    assert isinstance(session.ticket_lifetime_hint, int)
    assert isinstance(session.has_ticket, bool)
    assert pair.client.session_reused is False
