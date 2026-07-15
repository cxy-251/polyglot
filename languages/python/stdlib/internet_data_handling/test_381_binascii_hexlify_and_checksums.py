"""381｜hexlify/unhexlify 的 separator 方向与增量 CRC。

hexlify 返回长度恰为输入两倍的 bytes；bytes_per_sep 正数从右端分组，负数从左端分组，这对协议
字段布局很重要。unhexlify 要求纯十六进制且位数为偶数，比 bytes.fromhex 对空白更严格。crc32
和 crc_hqx 可用前一段结果作为下一段 seed，但它们是误码 checksum，不是抗碰撞密码学 hash。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.binascii.hexlify
# polyglot-covers: python.binascii.b2a_hex
# polyglot-covers: python.binascii.unhexlify
# polyglot-covers: python.binascii.a2b_hex
# polyglot-covers: python.binascii.hexlify-output-twice-input-length
# polyglot-covers: python.binascii.hexlify-separator
# polyglot-covers: python.binascii.hexlify-bytes-per-sep-right-count
# polyglot-covers: python.binascii.hexlify-negative-bytes-per-sep-left-count
# polyglot-covers: python.binascii.unhexlify-even-digits
# polyglot-covers: python.binascii.Error
# polyglot-covers: python.binascii.crc32
# polyglot-covers: python.binascii.crc32-incremental-seed
# polyglot-covers: python.binascii.crc32-unsigned
# polyglot-covers: python.binascii.crc_hqx
# polyglot-covers: python.binascii.checksum-not-cryptographic-hash

import binascii

import pytest


def test_hexlify_separator_direction_changes_field_grouping():
    payload = b"\xb9\x01\xef"
    assert binascii.hexlify(payload) == binascii.b2a_hex(payload) == b"b901ef"
    assert len(binascii.hexlify(payload)) == len(payload) * 2
    assert binascii.hexlify(payload, b"_", 2) == b"b9_01ef"
    assert binascii.hexlify(payload, "_", -2) == b"b901_ef"
    assert binascii.unhexlify("B901ef") == payload
    assert binascii.a2b_hex(b"b901ef") == payload


def test_unhexlify_rejects_odd_length_nonhex_and_embedded_whitespace():
    with pytest.raises(binascii.Error, match="Odd-length"):
        binascii.unhexlify("abc")
    with pytest.raises(binascii.Error, match="Non-hexadecimal"):
        binascii.unhexlify("zz")
    with pytest.raises(binascii.Error):
        binascii.unhexlify("b9 01")
    assert bytes.fromhex("b9 01") == b"\xb9\x01"


def test_crc_algorithms_accept_the_previous_chunk_result_as_seed():
    first, second = b"hello", b" world"
    whole_crc32 = binascii.crc32(first + second)
    chunked_crc32 = binascii.crc32(second, binascii.crc32(first))
    assert chunked_crc32 == whole_crc32
    assert 0 <= whole_crc32 <= 0xFFFFFFFF

    whole_hqx = binascii.crc_hqx(first + second, 0)
    chunked_hqx = binascii.crc_hqx(second, binascii.crc_hqx(first, 0))
    assert chunked_hqx == whole_hqx
    assert 0 <= whole_hqx <= 0xFFFF
