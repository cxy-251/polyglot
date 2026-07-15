"""383｜quoted-printable 的正文/header 模式、行尾空白与 binary stream。

quoted-printable 适合大部分可打印、少量 binary 的 MIME 内容。正文中行尾 space/tab 必须编码，
quotetabs 决定中间空白是否编码；header=True 把空格变 ``_``，并把原 underscore 编为 ``=5F``。
长行用 ``=\n`` soft break 折行，解码时移除；流接口始终读写 binary file object。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.quopri.encodestring
# polyglot-covers: python.quopri.decodestring
# polyglot-covers: python.quopri.quotetabs
# polyglot-covers: python.quopri.trailing-whitespace-always-encoded
# polyglot-covers: python.quopri.header-space-to-underscore
# polyglot-covers: python.quopri.header-literal-underscore-escaped
# polyglot-covers: python.quopri.soft-line-break
# polyglot-covers: python.quopri.encode-stream
# polyglot-covers: python.quopri.decode-stream
# polyglot-covers: python.quopri.binary-file-objects
# polyglot-covers: python.quopri.prefer-base64-for-mostly-binary-data

import io
import quopri


def test_body_mode_controls_embedded_but_not_trailing_whitespace():
    payload = b"embedded space\tand tab \nnon-ascii: \xff"
    readable = quopri.encodestring(payload, quotetabs=False)
    strict = quopri.encodestring(payload, quotetabs=True)
    assert b"embedded space" in readable
    assert b"embedded=20space" in strict
    assert b"tab=20\n" in readable
    assert b"=FF" in readable
    assert quopri.decodestring(readable) == payload
    assert quopri.decodestring(strict) == payload


def test_header_mode_distinguishes_encoded_spaces_from_literal_underscores():
    encoded = quopri.encodestring(b"display_name", header=True)
    assert encoded == b"display=5Fname"
    assert quopri.encodestring(b"display name", header=True) == b"display_name"
    assert quopri.decodestring(encoded, header=True) == b"display_name"
    assert quopri.decodestring(b"display_name", header=True) == b"display name"


def test_long_lines_use_soft_breaks_and_stream_api_round_trips_binary_data():
    payload = b"A" * 100 + b"\xff"
    encoded = quopri.encodestring(payload)
    assert b"=\n" in encoded
    assert all(len(line) <= 76 for line in encoded.splitlines())

    output = io.BytesIO()
    assert quopri.encode(io.BytesIO(payload), output, quotetabs=False) is None
    decoded = io.BytesIO()
    assert quopri.decode(io.BytesIO(output.getvalue()), decoded) is None
    assert decoded.getvalue() == payload
