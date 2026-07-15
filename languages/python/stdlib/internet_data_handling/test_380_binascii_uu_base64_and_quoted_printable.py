"""380｜binascii 的低层 UU、Base64 与 quoted-printable 转换。

binascii 是 base64/quopri/uu 等高层模块的 C 加速底座。b2a_uu 每次最多处理 45 bytes 并总带
换行；b2a_base64 可关闭换行。a2b_* 可接收纯 ASCII str，而 b2a_* 要求 bytes-like。quoted-
printable 的 header=True 会把 underscore 当作空格，这与正文模式不同。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.binascii.b2a_uu
# polyglot-covers: python.binascii.a2b_uu
# polyglot-covers: python.binascii.b2a-uu-at-most-45-bytes
# polyglot-covers: python.binascii.b2a-uu-backtick
# polyglot-covers: python.binascii.b2a_base64
# polyglot-covers: python.binascii.a2b_base64
# polyglot-covers: python.binascii.b2a-base64-newline
# polyglot-covers: python.binascii.a2b_qp
# polyglot-covers: python.binascii.b2a_qp
# polyglot-covers: python.binascii.qp-header-underscore-space
# polyglot-covers: python.binascii.a2b-accepts-ascii-str
# polyglot-covers: python.binascii.b2a-requires-bytes-like

import binascii

import pytest


def test_uu_line_round_trips_and_enforces_the_45_byte_limit():
    payload = b"\0binary\xff"
    normal = binascii.b2a_uu(payload)
    backtick = binascii.b2a_uu(payload, backtick=True)
    assert normal.endswith(b"\n")
    assert backtick.endswith(b"\n")
    assert b"`" in backtick
    assert binascii.a2b_uu(normal.decode("ascii")) == payload
    assert binascii.a2b_uu(backtick) == payload
    with pytest.raises(binascii.Error, match="45 bytes"):
        binascii.b2a_uu(b"x" * 46)


def test_low_level_base64_controls_the_single_trailing_newline():
    assert binascii.b2a_base64(b"abc") == b"YWJj\n"
    assert binascii.b2a_base64(memoryview(b"abc"), newline=False) == b"YWJj"
    assert binascii.a2b_base64("YWJj\nYWJj") == b"abcabc"
    with pytest.raises(TypeError):
        binascii.b2a_base64("abc")


def test_low_level_quoted_printable_header_mode_maps_spaces_and_underscores():
    encoded = binascii.b2a_qp(b"display name_with underscore", header=True)
    assert encoded == b"display_name=5Fwith_underscore"
    assert binascii.a2b_qp(encoded, header=True) == b"display name_with underscore"
    assert binascii.a2b_qp(b"body_has_underscore", header=False) == b"body_has_underscore"
