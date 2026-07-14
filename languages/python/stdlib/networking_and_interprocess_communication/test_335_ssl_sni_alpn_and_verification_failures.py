"""335｜SNI callback、ALPN negotiation 与 handshake verification failure。

server_hostname 同时用于 SNI virtual-host selection 和 client hostname verification。server callback
可按 name 切换 SSLObject.context；异常应返回 AlertDescription 而不是跨 C callback 抛出。ALPN
按双方有序列表选一个共同 application protocol。信任链失败和 hostname mismatch 都在 handshake
阶段抛 SSLCertVerificationError，并给出 verify_code/verify_message。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.SSLContext.set_servername_callback
# polyglot-covers: python.ssl.sni-servername-callback-sslobj-name-context
# polyglot-covers: python.ssl.sni-callback-context-switch
# polyglot-covers: python.ssl.sni-callback-alert-description-on-error
# polyglot-covers: python.ssl.AlertDescription
# polyglot-covers: python.ssl.SSLContext.set_alpn_protocols
# polyglot-covers: python.ssl.SSLObject.selected_alpn_protocol
# polyglot-covers: python.ssl.alpn-common-protocol-negotiation
# polyglot-covers: python.ssl.alpn-protocol-one-to-255-bytes
# polyglot-covers: python.ssl.server-hostname-enables-sni
# polyglot-covers: python.ssl.server-hostname-enables-hostname-check
# polyglot-covers: python.ssl.hostname-mismatch-handshake-failure
# polyglot-covers: python.ssl.untrusted-chain-handshake-failure
# polyglot-covers: python.ssl.SSLCertVerificationError.verify_code
# polyglot-covers: python.ssl.SSLCertVerificationError.verify_message

import ssl

import pytest

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate
from test_334_ssl_memory_bio_handshake_and_data import MemoryTLSPair


def _server_context(tmp_path):
    certificate, private_key = write_test_certificate(tmp_path)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, private_key)
    return context


def _trusted_client_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cadata=CERTIFICATE_PEM)
    return context


def test_sni_callback_observes_hostname_and_alpn_selects_a_common_protocol(tmp_path):
    server_context = _server_context(tmp_path)
    client_context = _trusted_client_context()
    seen = []

    def choose_virtual_host(ssl_object, server_name, initial_context):
        seen.append((ssl_object, server_name, initial_context))
        ssl_object.context = server_context
        return None

    server_context.set_servername_callback(choose_virtual_host)
    server_context.set_alpn_protocols(["h2", "http/1.1"])
    client_context.set_alpn_protocols(["http/1.1"])
    pair = MemoryTLSPair(client_context, server_context, "localhost")
    assert pair.client.selected_alpn_protocol() is None
    pair.handshake()

    assert len(seen) == 1
    ssl_object, server_name, initial_context = seen[0]
    assert ssl_object is pair.server
    assert server_name == "localhost"
    assert initial_context is server_context
    assert pair.client.selected_alpn_protocol() == "http/1.1"
    assert pair.server.selected_alpn_protocol() == "http/1.1"


def test_alpn_rejects_an_individual_protocol_longer_than_one_byte_length_field():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    with pytest.raises(ssl.SSLError):
        context.set_alpn_protocols(["x" * 256])


def test_hostname_mismatch_raises_detailed_verification_error(tmp_path):
    pair = MemoryTLSPair(
        _trusted_client_context(),
        _server_context(tmp_path),
        "wrong.example.test",
    )
    with pytest.raises(ssl.SSLCertVerificationError) as caught:
        pair.handshake()

    assert isinstance(caught.value.verify_code, int)
    assert "hostname" in caught.value.verify_message.lower()


def test_untrusted_self_signed_chain_fails_before_application_data(tmp_path):
    untrusted_client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    pair = MemoryTLSPair(
        untrusted_client,
        _server_context(tmp_path),
        "localhost",
    )
    with pytest.raises(ssl.SSLCertVerificationError) as caught:
        pair.handshake()

    assert isinstance(caught.value.verify_code, int)
    assert caught.value.verify_message
