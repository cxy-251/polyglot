"""379｜Base64 legacy 文件接口与 RFC 2045 每行 76 字符。

legacy encode/encodebytes 为 MIME 风格输出插入最多 76 字符的行并保证末尾换行；现代 b64encode
不换行。decode 从 binary input 的 readline 逐行消费并写 binary output，不接受现代接口支持的
ASCII str。真正构造 MIME 邮件时应使用 email 包，让它同时维护 Content-Transfer-Encoding header。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.base64.encodebytes
# polyglot-covers: python.base64.decodebytes
# polyglot-covers: python.base64.encode-legacy-file-interface
# polyglot-covers: python.base64.decode-legacy-file-interface
# polyglot-covers: python.base64.legacy-binary-file-objects
# polyglot-covers: python.base64.legacy-rfc2045-line-length-76
# polyglot-covers: python.base64.legacy-output-trailing-newline
# polyglot-covers: python.base64.modern-output-no-line-wrap
# polyglot-covers: python.base64.prefer-email-package-for-mime

import base64
import io


def test_encodebytes_wraps_mime_lines_while_modern_encoding_does_not():
    payload = b"x" * 60
    modern = base64.b64encode(payload)
    legacy = base64.encodebytes(payload)
    assert len(modern) == 80
    assert b"\n" not in modern
    assert [len(line) for line in legacy.splitlines()] == [76, 4]
    assert legacy.endswith(b"\n")
    assert base64.decodebytes(legacy) == payload


def test_legacy_encode_and_decode_stream_between_binary_file_objects():
    payload = bytes(range(256))
    encoded = io.BytesIO()
    assert base64.encode(io.BytesIO(payload), encoded) is None
    assert encoded.getvalue().endswith(b"\n")
    assert all(len(line) <= 76 for line in encoded.getvalue().splitlines())

    decoded = io.BytesIO()
    assert base64.decode(io.BytesIO(encoded.getvalue()), decoded) is None
    assert decoded.getvalue() == payload
