"""100｜certificate PEM/DER、hostname matching、时间、随机数与异常体系。

本文件内嵌一张只供测试的长期自签名 localhost CA/server certificate 和公开 private key；它不是
秘密，也绝不能用于真实服务。后续 TLS 案例把它写入 tmp_path，不依赖 openssl 命令或外部网络。
PEM 是 base64 armor，DER 是同一 ASN.1 certificate 的二进制表示，可无损往返。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.ssl.DER_cert_to_PEM_cert
# polyglot-covers: python.ssl.PEM_cert_to_DER_cert
# polyglot-covers: python.ssl.pem-der-certificate-roundtrip
# polyglot-covers: python.ssl.cert_time_to_seconds
# polyglot-covers: python.ssl.certificate-time-gmt
# polyglot-covers: python.ssl.match_hostname
# polyglot-covers: python.ssl.match-hostname-subject-alt-name
# polyglot-covers: python.ssl.match-hostname-leftmost-wildcard
# polyglot-covers: python.ssl.match-hostname-ip-address
# polyglot-covers: python.ssl.match-hostname-failure-certificate-error
# polyglot-covers: python.ssl.match-hostname-deprecated-3.7
# polyglot-covers: python.ssl.get_default_verify_paths
# polyglot-covers: python.ssl.DefaultVerifyPaths
# polyglot-covers: python.ssl.RAND_status
# polyglot-covers: python.ssl.RAND_bytes
# polyglot-covers: python.ssl.RAND_add
# polyglot-covers: python.ssl.os-urandom-preferred-over-rand-api
# polyglot-covers: python.ssl.SSLError
# polyglot-covers: python.ssl.SSLZeroReturnError
# polyglot-covers: python.ssl.SSLWantReadError
# polyglot-covers: python.ssl.SSLWantWriteError
# polyglot-covers: python.ssl.SSLSyscallError
# polyglot-covers: python.ssl.SSLEOFError
# polyglot-covers: python.ssl.SSLCertVerificationError
# polyglot-covers: python.ssl.CertificateError-alias




import ssl
import pytest
import concurrent.futures
import socket

CERTIFICATE_PEM = """-----BEGIN CERTIFICATE-----
MIIDATCCAemgAwIBAgIJAKHGj8u9SNRwMA0GCSqGSIb3DQEBCwUAMBQxEjAQBgNV
BAMMCWxvY2FsaG9zdDAgFw0yNjA3MTQxODIxMDFaGA8yMTI2MDYyMDE4MjEwMVow
FDESMBAGA1UEAwwJbG9jYWxob3N0MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEA53IVpFEhyo3dAqeWDlbD2UK5ku5POqE/DmP7VXkQM/sRDoqmZjouzMmi
Pl8QcILjREbZ5RiT1ws1z6I8UdVQRRl6cXS0hPVu7CBMUrxPWbJc1NvOlSaaS6a4
FoTkioKE6cihSFd7DKEE9/3bI0KkboxP2nbMaTZ7ljqWDOLO6k11IEJYnzydhXp0
QhKX+LUEDBv+X3D7WYfGfNW6Vou8C14eIqoILgiq7YzY/whwaVbfiGrXgJCrjuAl
fhj9zi0xzblhhekB2hbsEkX/kJG7i34TZznKcJs0O79kYjWiTV2hzZWwVpJ1XIk6
vcZAHa+funiGq4Z2bQO0Sy4WFVB0VQIDAQABo1QwUjAPBgNVHRMBAf8EBTADAQH/
MA4GA1UdDwEB/wQEAwICpDATBgNVHSUEDDAKBggrBgEFBQcDATAaBgNVHREEEzAR
gglsb2NhbGhvc3SHBH8AAAEwDQYJKoZIhvcNAQELBQADggEBAA+vVBoThMoLXz1d
3mJQ34GyG/i2IEFr3cSIwAyRvbFZM/bfV7g2Et5rso3d6su9Cw/6xorxixY9yjQC
cu5cfY3wKNmQ1kxwuZiQeu6MBcp+uqqFAoCLr2y59wtDaQtzzZREfWCh1OI3yYKr
2SVUcHejP4GKXrQy5d2BNQd/jFrhkhMU3KBIIf6drkvgfTjMmcT3qvedjEquZiw7
veg6HzDvVYgWCp1m19d3wOBLIfKtNuzJkcGXWeg9AcncbSQwIg5W63JoikxU4eFN
dd51MUN1hZ20TQkaSP7Q/9UTKJXgrKSb1AHPYQLunVder7Ut5YTEcM/RANbGviPM
xlKyxb0=
-----END CERTIFICATE-----
"""


PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDnchWkUSHKjd0C
p5YOVsPZQrmS7k86oT8OY/tVeRAz+xEOiqZmOi7MyaI+XxBwguNERtnlGJPXCzXP
ojxR1VBFGXpxdLSE9W7sIExSvE9ZslzU286VJppLprgWhOSKgoTpyKFIV3sMoQT3
/dsjQqRujE/adsxpNnuWOpYM4s7qTXUgQlifPJ2FenRCEpf4tQQMG/5fcPtZh8Z8
1bpWi7wLXh4iqgguCKrtjNj/CHBpVt+IateAkKuO4CV+GP3OLTHNuWGF6QHaFuwS
Rf+QkbuLfhNnOcpwmzQ7v2RiNaJNXaHNlbBWknVciTq9xkAdr5+6eIarhnZtA7RL
LhYVUHRVAgMBAAECggEBANZITPs+Vp/XqokbqhWKhXdwjKoZ0+b/hYcIUJm5JaRK
zmb9PcSmF9Bo2rsOfwT8WfhL9M9kavSNn3umxFwruE7RoQjMOZpkNheOa7uqN3lf
Zw14mRKElBR4vjWzQnlvECn3JEP7IqT1q8kDEtHZkK39YK1ukiDTXacghO5XS6Wm
4IH2lKNL71vBdNFDCsmkjGwSTAg9CaNzbuWQcqHzD1LoOnqaCwV0F+SfYRAEDxgD
2gC/2vZvB3lnbnQdndv8KKCIEK77i+yxLO97PmAlN1AcYi/8JkvtkvgCcd1KQsso
EdKN8/YKETie1RMz2bqp5oUi4p8dxFcIMUzLHrPSS+ECgYEA9zbd08hQJcectTyp
BithvBhg1AOZoSxQ/tZqGmBgPpocJD3j7+NBwmlUb5kvtiz6khhGykpdCaxHLdn6
InXv71a+eRR1gQaVlE4DXBrR56VPcO+a7b9N5pQZIaRdsTIjI1f/R+6ZcaahS020
oFbOp+a4w2JDd/bRejzEpcrvAy0CgYEA76vBicn9Z43vKPiuClzx6c0U26mdd517
oAQnYonwiTFQxVEA0T/bibt0haJk0ip+OUKM3N1BZkjsPmjJnoUo2XU1m1xXnZlk
N0xWQfw/DTWh8c4fX55A4gLxqPuz752CbMMPEzXuKGJL79E9BY0Wb3rFhdtMdJZ8
lQYG3dn0jskCgYEAkLfIwfqomIUzApHBLMBmlXL79AErhUNpItWoBUrX7K3QvZKR
hdPWohWA/VeCq7XG9ZFKl49SyZ/Vh0zsdhHuZIC2PjEw3FhbZhcJNnjo2h9W0vkh
C/6KfunBkIUk598+3Kjd42EU6IgwMeIKVDadAYM6M/6pGmgdlt5OC/QxWP0CgYA+
YMSJeTHj3tQNJNQfTFuGD2NLXJToSeugFRSvF9mry1MLV+7Ph0A7U7ebBE4bSQX7
HzAMV+WqmnYqNBmtkVi1aEUgf2MqWH71yX91wxIh/QB+L7iIqWaXrE57Pa9yQNtu
NUJaLKIkjpjW/O1V4YeiUiDQmugGPBiGrL/iw9RbyQKBgDNycF1CffptAruTIx52
yPEaFlBoJ1SkZmScpNSEPo0YGVkcWnzIXUmpAD9Sk2lXffqswpFUCn2ucGKmCOSH
5oiLHD+L0fStsIGYQ/uI52kWZ6slbfj4TPV0LIYklvKV05h42V+VOa6VEjICXOsj
q2onQOhHA3N78n7lLuMG4e0n
-----END PRIVATE KEY-----
"""


def write_test_certificate(tmp_path):
    certificate = tmp_path / "localhost-cert.pem"
    private_key = tmp_path / "localhost-key.pem"
    certificate.write_text(CERTIFICATE_PEM, encoding="ascii")
    private_key.write_text(PRIVATE_KEY_PEM, encoding="ascii")
    return certificate, private_key


def test_pem_der_conversion_round_trips_the_same_certificate():
    der = ssl.PEM_cert_to_DER_cert(CERTIFICATE_PEM)
    rebuilt_pem = ssl.DER_cert_to_PEM_cert(der)
    assert isinstance(der, bytes)
    assert ssl.PEM_cert_to_DER_cert(rebuilt_pem) == der


def test_certificate_time_is_parsed_as_utc_gmt():
    assert ssl.cert_time_to_seconds("Jan  5 09:34:43 2018 GMT") == 1515144883


def test_deprecated_manual_hostname_match_handles_san_wildcard_and_ip():
    certificate = {
        "subjectAltName": (
            ("DNS", "*.example.test"),
            ("IP Address", "127.0.0.1"),
        )
    }
    with pytest.deprecated_call():
        assert ssl.match_hostname(certificate, "api.example.test") is None
    with pytest.deprecated_call():
        assert ssl.match_hostname(certificate, "127.0.0.1") is None
    with pytest.deprecated_call():
        with pytest.raises(ssl.CertificateError):
            ssl.match_hostname(certificate, "deep.api.example.test")


def test_random_and_default_verify_path_helpers_expose_environment_state():
    assert ssl.RAND_status() is True
    assert len(ssl.RAND_bytes(16)) == 16
    ssl.RAND_add(b"not claimed as entropy", 0.0)

    paths = ssl.get_default_verify_paths()
    assert isinstance(paths, ssl.DefaultVerifyPaths)
    assert paths.openssl_cafile_env
    assert paths.openssl_capath_env


def test_ssl_exceptions_share_the_documented_hierarchy_and_alias():
    subclasses = [
        ssl.SSLZeroReturnError,
        ssl.SSLWantReadError,
        ssl.SSLWantWriteError,
        ssl.SSLSyscallError,
        ssl.SSLEOFError,
        ssl.SSLCertVerificationError,
    ]
    assert issubclass(ssl.SSLError, OSError)
    assert all(issubclass(item, ssl.SSLError) for item in subclasses)
    assert ssl.CertificateError is ssl.SSLCertVerificationError


# SSLContext client/server defaults、verification ordering、versions 与 cipher policy。
#
# PROTOCOL_TLS_CLIENT 默认 CERT_REQUIRED + check_hostname；SERVER 默认不验证 client certificate。
# check_hostname 为 True 时不能降到 CERT_NONE，设置顺序本身是常见坑。minimum/maximum_version
# 取代 OP_NO_TLS*；set_ciphers 只配置 TLS 1.2 及更早 cipher，不能关闭 TLS 1.3 cipher suites。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# SSLContext 加载 server chain、CA trust 与 certificate store introspection。
#
# load_cert_chain 同时需要 certificate chain 和匹配 private key；load_verify_locations 加入信任锚，
# 不是加载本端 identity。cadata 可直接给 PEM text。get_ca_certs(binary_form=False) 返回 decoded
# dict，True 返回 DER；cert_store_stats 区分总 X.509、CA 和 CRL 数量。fixture 只写 tmp_path。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.ssl.SSLContext.load_cert_chain
# polyglot-covers: python.ssl.cert-chain-private-key-must-match
# polyglot-covers: python.ssl.SSLContext.load_verify_locations
# polyglot-covers: python.ssl.load-verify-locations-cafile
# polyglot-covers: python.ssl.load-verify-locations-cadata-pem
# polyglot-covers: python.ssl.identity-chain-vs-trust-store
# polyglot-covers: python.ssl.SSLContext.get_ca_certs
# polyglot-covers: python.ssl.get-ca-certs-decoded
# polyglot-covers: python.ssl.get-ca-certs-binary-der
# polyglot-covers: python.ssl.SSLContext.cert_store_stats
# polyglot-covers: python.ssl.cert-store-x509-ca-crl-counts
# polyglot-covers: python.ssl.SSLContext.set_default_verify_paths
# polyglot-covers: python.ssl.SSLContext.load_default_certs




def _subject_common_names(decoded_certificates):
    names = []
    for certificate in decoded_certificates:
        for relative_name in certificate.get("subject", ()):
            for key, value in relative_name:
                if key == "commonName":
                    names.append(value)
    return names


def test_server_identity_and_client_trust_use_different_context_methods(tmp_path):
    certificate, private_key = write_test_certificate(tmp_path)
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    assert server.load_cert_chain(certificate, private_key) is None

    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    before = client.cert_store_stats()
    assert client.load_verify_locations(cadata=CERTIFICATE_PEM) is None
    after = client.cert_store_stats()

    assert after["x509"] >= before["x509"] + 1
    assert after["x509_ca"] >= before["x509_ca"] + 1
    assert after["crl"] == before["crl"]
    assert "localhost" in _subject_common_names(client.get_ca_certs())

    expected_der = ssl.PEM_cert_to_DER_cert(CERTIFICATE_PEM)
    assert expected_der in client.get_ca_certs(binary_form=True)


def test_cafile_and_default_path_loading_are_separate_trust_sources(tmp_path):
    certificate, _ = write_test_certificate(tmp_path)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=certificate)
    assert "localhost" in _subject_common_names(context.get_ca_certs())

    defaults = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    assert defaults.set_default_verify_paths() is None
    assert defaults.load_default_certs(ssl.Purpose.SERVER_AUTH) is None
    assert set(defaults.cert_store_stats()) == {"x509", "crl", "x509_ca"}


# MemoryBIO/SSLObject 驱动无 socket 的完整 TLS state machine。
#
# SSLObject 只处理协议，不做 network I/O：incoming BIO 接收 wire bytes，outgoing BIO 产出待发送
# bytes。framework 在每次 SSLWantRead/Write 后把数据搬到对端并按 readiness 重试。案例在内存中
# 完成 certificate verification、hostname check、加密 application data 和连接 metadata 查询。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# SNI callback、ALPN negotiation 与 handshake verification failure。
#
# server_hostname 同时用于 SNI virtual-host selection 和 client hostname verification。server callback
# 可按 name 切换 SSLObject.context；异常应返回 AlertDescription 而不是跨 C callback 抛出。ALPN
# 按双方有序列表选一个共同 application protocol。信任链失败和 hostname mismatch 都在 handshake
# 阶段抛 SSLCertVerificationError，并给出 verify_code/verify_message。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# SSLSocket 显式 handshake、加密 I/O、metadata 与 unwrap。
#
# wrap_socket 接管已有 SOCK_STREAM，返回与 context 绑定的 SSLSocket；do_handshake_on_connect=False
# 让调用者控制 handshake。两端 handshake/unwrap 都会互等 wire data，本例用线程并发推进但不访问
# 网络。unwrap 完成 TLS close-notify 后返回新的 plain socket，后续不能继续使用原 SSL wrapper。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# non-blocking SSLSocket retry 与 SSLContext wrapper class/configuration hooks。
#
# 普通 socket 的 EAGAIN 在 TLS 层变成 SSLWantRead/Write；操作方向和所需底层 readiness 可能相反，
# 必须按异常等待对应 fd 后重试完整调用。sslsocket_class/sslobject_class 允许 framework 插入子类。
# keylog_filename 仅用于调试且会泄露 session secrets；生产环境不能随意启用或提交其输出。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# get_server_certificate 与 deprecated module-level wrap_socket。
#
# get_server_certificate 是会主动连接的 convenience API；本例只连接容器内 127.0.0.1 随机端口，
# 获取 PEM 并可用 ca_certs 验证。module-level wrap_socket 不支持 SNI/hostname matching，且每次创建
# 临时 context，3.7 起已弃用；新代码必须复用显式 SSLContext。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.ssl.get_server_certificate
# polyglot-covers: python.ssl.get-server-certificate-pem
# polyglot-covers: python.ssl.get-server-certificate-timeout-3.10
# polyglot-covers: python.ssl.get-server-certificate-ca-validation
# polyglot-covers: python.ssl.get-server-certificate-active-connection
# polyglot-covers: python.ssl.wrap_socket-module-function
# polyglot-covers: python.ssl.module-wrap-socket-deprecated-3.7
# polyglot-covers: python.ssl.module-wrap-socket-no-sni-hostname-check
# polyglot-covers: python.ssl.context-wrap-socket-preferred





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


# SSLSession 注入与 TLS 1.2 session resumption。
#
# 同一个 client context 可把首次 handshake 的 SSLSession 传给后续 wrap_bio；server context 必须
# 保持相同，才能命中其 session cache。TLS 1.3 ticket 在 handshake 后异步到达，演示更复杂；本例
# 固定 TLS 1.2，使 session ID 在 handshake 完成时即可复用。session 不能跨不同 SSLContext 使用。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.ssl.wrap-bio-session-parameter
# polyglot-covers: python.ssl.ssl-session-client-injection-before-handshake
# polyglot-covers: python.ssl.ssl-session-same-context-required
# polyglot-covers: python.ssl.ssl-session-server-cache
# polyglot-covers: python.ssl.ssl-session-tls12-id-resumption
# polyglot-covers: python.ssl.ssl-session-tls13-ticket-arrives-post-handshake
# polyglot-covers: python.ssl.session_reused
# polyglot-covers: python.ssl.session-stats-cache-hit




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
