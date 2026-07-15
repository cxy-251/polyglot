"""409｜Charset 的规范化、编码策略与按行 header 编码。

Charset 不是通用文本编解码器，而是 legacy email 的字符集策略对象：它记录输入/输出 codec、
header/body 的传输编码和输出 charset。utf-8 header 可在 QP/base64 中选较短者，body 固定
base64；us-ascii 则保持 7bit。多字节 header 应使用 header_encode_lines 避免在字节中间切断。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.charset.Charset
# polyglot-covers: python.email.charset.Charset-alias-normalization
# polyglot-covers: python.email.charset.Charset.input_charset
# polyglot-covers: python.email.charset.Charset.output_charset
# polyglot-covers: python.email.charset.Charset.input_codec
# polyglot-covers: python.email.charset.Charset.output_codec
# polyglot-covers: python.email.charset.Charset.header_encoding
# polyglot-covers: python.email.charset.Charset.body_encoding
# polyglot-covers: python.email.charset.Charset.get_body_encoding
# polyglot-covers: python.email.charset.Charset.get_output_charset
# polyglot-covers: python.email.charset.Charset.header_encode
# polyglot-covers: python.email.charset.Charset.header_encode_lines
# polyglot-covers: python.email.charset.Charset.body_encode
# polyglot-covers: python.email.charset.Charset.__str__
# polyglot-covers: python.email.charset.Charset.__eq__
# polyglot-covers: python.email.charset.Charset.__ne__

import base64
from email.charset import BASE64, SHORTEST, Charset
from email.header import decode_header


def test_charset_normalizes_aliases_and_exposes_transport_policy():
    latin = Charset("latin_1")
    utf8 = Charset("utf-8")
    ascii_charset = Charset("us-ascii")

    assert latin.input_charset == "iso-8859-1"
    assert str(latin) == "iso-8859-1"
    assert latin == Charset("iso-8859-1")
    assert latin != utf8
    assert utf8.output_charset == "utf-8"
    assert utf8.input_codec == "utf-8"
    assert utf8.output_codec == "utf-8"
    assert utf8.header_encoding == SHORTEST
    assert utf8.body_encoding == BASE64
    assert utf8.get_body_encoding() == "base64"
    assert utf8.get_output_charset() == "utf-8"
    assert ascii_charset.get_body_encoding() == "7bit"


def test_charset_encodes_headers_and_bodies_according_to_different_constraints():
    utf8 = Charset("utf-8")
    header = utf8.header_encode("中文")
    body = utf8.body_encode("中文")

    decoded_piece, declared_charset = decode_header(header)[0]
    assert decoded_piece.decode(declared_charset) == "中文"
    assert base64.b64decode(body) == "中文".encode()

    # maxlengths 是逐行预算迭代器；返回值已保证 encoded-word 不会把 UTF-8 字符切半。
    lines = utf8.header_encode_lines("数据" * 8, iter([32] * 20))
    assert len(lines) > 1
    assert all(line is None or len(line) <= 32 for line in lines)
