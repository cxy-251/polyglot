"""331｜certificate PEM/DER、hostname matching、时间、随机数与异常体系。

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
