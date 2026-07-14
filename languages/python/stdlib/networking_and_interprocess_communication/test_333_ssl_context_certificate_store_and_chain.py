"""333｜SSLContext 加载 server chain、CA trust 与 certificate store introspection。

load_cert_chain 同时需要 certificate chain 和匹配 private key；load_verify_locations 加入信任锚，
不是加载本端 identity。cadata 可直接给 PEM text。get_ca_certs(binary_form=False) 返回 decoded
dict，True 返回 DER；cert_store_stats 区分总 X.509、CA 和 CRL 数量。fixture 只写 tmp_path。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import ssl

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate


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
