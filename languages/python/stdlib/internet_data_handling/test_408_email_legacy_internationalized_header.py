"""408｜legacy Header 的多字符集片段、折行、解码与重建。

Header 用 RFC 2047 encoded-word 把非 ASCII 标题放进 7-bit 邮件头；append 可声明 bytes 的
源字符集，encode 控制线长与换行符，decode_header 则只拆成 bytes/charset 对而不替调用方
统一解码。现代 EmailMessage 会自动完成这些工作，Header 主要用于旧代码或精确编码控制。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.header.Header
# polyglot-covers: python.email.header.Header.append
# polyglot-covers: python.email.header.Header-bytes-source-charset
# polyglot-covers: python.email.header.Header.encode
# polyglot-covers: python.email.header.Header-linesep
# polyglot-covers: python.email.header.Header-header-name-first-line-budget
# polyglot-covers: python.email.header.Header-continuation-whitespace
# polyglot-covers: python.email.header.Header.__str__
# polyglot-covers: python.email.header.Header.__eq__
# polyglot-covers: python.email.header.Header.__ne__
# polyglot-covers: python.email.header.Header-bytes-decode-error
# polyglot-covers: python.email.header.decode_header
# polyglot-covers: python.email.header.make_header

from email.header import Header, decode_header, make_header

import pytest


def test_header_combines_unicode_and_bytes_pieces_with_declared_charsets():
    header = Header("Résumé", "utf-8")
    header.append("for", "us-ascii")
    header.append(b"Andr\xe9", "iso-8859-1")

    encoded = header.encode()
    assert "=?utf-8?" in encoded.lower()
    assert "=?iso-8859-1?" in encoded.lower()
    assert str(header) == "Résumé for André"


def test_header_folding_accounts_for_field_name_and_uses_requested_line_separator():
    value = "alpha, beta, gamma, delta, epsilon, zeta"
    header = Header(
        value,
        maxlinelen=24,
        header_name="Subject",
        continuation_ws="\t",
    )
    encoded = header.encode(linesep="\r\n")

    assert "\r\n\t" in encoded
    assert all(len(line) <= 24 for line in encoded.split("\r\n"))


def test_decode_header_preserves_piece_charsets_and_make_header_reconstructs_text():
    wire = "=?iso-8859-1?q?Andr=E9?= <andre@example.test>"
    pieces = decode_header(wire)

    assert pieces[0] == (b"Andr\xe9", "iso-8859-1")
    assert str(make_header(pieces)) == "André <andre@example.test>"
    assert Header("same", "us-ascii") == Header("same", "us-ascii")
    assert Header("same", "us-ascii") != Header("different", "us-ascii")


def test_bytes_piece_is_decoded_using_its_declared_charset():
    with pytest.raises(UnicodeDecodeError):
        Header(b"\xff", "ascii")
