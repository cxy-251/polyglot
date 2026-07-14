"""332｜SSLContext client/server defaults、verification ordering、versions 与 cipher policy。

PROTOCOL_TLS_CLIENT 默认 CERT_REQUIRED + check_hostname；SERVER 默认不验证 client certificate。
check_hostname 为 True 时不能降到 CERT_NONE，设置顺序本身是常见坑。minimum/maximum_version
取代 OP_NO_TLS*；set_ciphers 只配置 TLS 1.2 及更早 cipher，不能关闭 TLS 1.3 cipher suites。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.SSLContext
# polyglot-covers: python.ssl.PROTOCOL_TLS_CLIENT
# polyglot-covers: python.ssl.PROTOCOL_TLS_SERVER
# polyglot-covers: python.ssl.PROTOCOL_TLS-deprecated-3.10
# polyglot-covers: python.ssl.create_default_context
# polyglot-covers: python.ssl.Purpose.SERVER_AUTH
# polyglot-covers: python.ssl.Purpose.CLIENT_AUTH
# polyglot-covers: python.ssl.SSLContext.protocol
# polyglot-covers: python.ssl.SSLContext.verify_mode
# polyglot-covers: python.ssl.SSLContext.check_hostname
# polyglot-covers: python.ssl.check-hostname-requires-cert-verification
# polyglot-covers: python.ssl.CERT_NONE
# polyglot-covers: python.ssl.CERT_OPTIONAL
# polyglot-covers: python.ssl.CERT_REQUIRED
# polyglot-covers: python.ssl.VerifyMode
# polyglot-covers: python.ssl.SSLContext.minimum_version
# polyglot-covers: python.ssl.SSLContext.maximum_version
# polyglot-covers: python.ssl.TLSVersion
# polyglot-covers: python.ssl.version-range-preferred-over-op-no-tls
# polyglot-covers: python.ssl.SSLContext.options
# polyglot-covers: python.ssl.Options
# polyglot-covers: python.ssl.SSLContext.verify_flags
# polyglot-covers: python.ssl.VerifyFlags
# polyglot-covers: python.ssl.VERIFY_X509_TRUSTED_FIRST
# polyglot-covers: python.ssl.VERIFY_ALLOW_PROXY_CERTS-3.10
# polyglot-covers: python.ssl.VERIFY_X509_PARTIAL_CHAIN-3.10
# polyglot-covers: python.ssl.SSLContext.set_ciphers
# polyglot-covers: python.ssl.SSLContext.get_ciphers
# polyglot-covers: python.ssl.set-ciphers-does-not-configure-tls13
# polyglot-covers: python.ssl.SSLContext.security_level
# polyglot-covers: python.ssl.OPENSSL_VERSION
# polyglot-covers: python.ssl.OPENSSL_VERSION_INFO
# polyglot-covers: python.ssl.openssl-minimum-1.1.1-python-3.10

import ssl

import pytest


def test_client_and_server_protocols_choose_opposite_verification_defaults():
    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    assert client.protocol == ssl.PROTOCOL_TLS_CLIENT
    assert client.verify_mode == ssl.CERT_REQUIRED
    assert client.check_hostname is True
    assert server.protocol == ssl.PROTOCOL_TLS_SERVER
    assert server.verify_mode == ssl.CERT_NONE
    assert server.check_hostname is False

    with pytest.raises(ValueError, match="check_hostname"):
        client.verify_mode = ssl.CERT_NONE
    client.check_hostname = False
    client.verify_mode = ssl.CERT_NONE
    assert client.verify_mode == ssl.CERT_NONE


def test_default_context_uses_purpose_specific_secure_defaults():
    client = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    server = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    assert client.protocol == ssl.PROTOCOL_TLS_CLIENT
    assert client.verify_mode == ssl.CERT_REQUIRED
    assert client.check_hostname is True
    assert server.protocol == ssl.PROTOCOL_TLS_SERVER
    assert server.check_hostname is False


def test_generic_protocol_is_deprecated_in_favor_of_role_specific_protocols():
    with pytest.deprecated_call():
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    assert context.protocol == ssl.PROTOCOL_TLS


def test_version_options_verify_flags_and_security_level_are_typed_policies():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED

    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.MAXIMUM_SUPPORTED
    assert isinstance(context.options, ssl.Options)
    assert isinstance(context.verify_flags, ssl.VerifyFlags)
    assert context.verify_flags & ssl.VERIFY_X509_TRUSTED_FIRST
    assert isinstance(ssl.VERIFY_ALLOW_PROXY_CERTS, ssl.VerifyFlags)
    assert isinstance(ssl.VERIFY_X509_PARTIAL_CHAIN, ssl.VerifyFlags)
    assert isinstance(context.security_level, int)


def test_cipher_configuration_returns_descriptive_records():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.set_ciphers("ECDHE+AESGCM")
    ciphers = context.get_ciphers()

    assert ciphers
    assert all({"name", "protocol", "strength_bits"} <= item.keys() for item in ciphers)
    # OpenSSL 1.1.1+ 的 TLS 1.3 suites 仍在列表中，set_ciphers 不会移除它们。
    assert any(item["protocol"] == "TLSv1.3" for item in ciphers)
    assert isinstance(ssl.OPENSSL_VERSION, str)
    assert ssl.OPENSSL_VERSION_INFO >= (1, 1, 1)
