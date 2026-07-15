"""377｜Base16/Base32 大小写、易混字符与 Python 3.10 Base32hex。

Base16/32 默认只接受规范大写。casefold=True 是兼容开关；Base32 的 map01 还可把 0 映射 O、把
1 映射 I 或 L，但默认因安全原因禁用，避免人眼凭据出现歧义。Extended Hex Base32 在 3.10 新增，
0/1 本就是其字母表成员，不能做上述替换。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.base64.b16encode
# polyglot-covers: python.base64.b16decode
# polyglot-covers: python.base64.b16decode-casefold
# polyglot-covers: python.base64.b32encode
# polyglot-covers: python.base64.b32decode
# polyglot-covers: python.base64.b32decode-casefold
# polyglot-covers: python.base64.b32decode-map01
# polyglot-covers: python.base64.base32-ambiguous-digits-disabled-by-default
# polyglot-covers: python.base64.b32hexencode
# polyglot-covers: python.base64.b32hexdecode
# polyglot-covers: python.base64.base32hex-new-in-3.10
# polyglot-covers: python.base64.base32hex-no-map01

import base64
import binascii

import pytest


def test_base16_and_base32_require_uppercase_unless_casefold_is_enabled():
    assert base64.b16encode(b"\xfa\xce") == b"FACE"
    with pytest.raises(binascii.Error):
        base64.b16decode(b"face")
    assert base64.b16decode(b"face", casefold=True) == b"\xfa\xce"

    encoded = base64.b32encode(b"polyglot")
    with pytest.raises(binascii.Error):
        base64.b32decode(encoded.lower())
    assert base64.b32decode(encoded.lower(), casefold=True) == b"polyglot"


def test_base32_map01_explicitly_accepts_an_ambiguous_human_transcription():
    payload, encoded = next(
        (bytes([value]), base64.b32encode(bytes([value])))
        for value in range(256)
        if b"O" in base64.b32encode(bytes([value]))
    )
    transcribed = encoded.replace(b"O", b"0")
    with pytest.raises(binascii.Error):
        base64.b32decode(transcribed)
    assert base64.b32decode(transcribed, map01=b"I") == payload

    payload, encoded = next(
        (bytes([value]), base64.b32encode(bytes([value])))
        for value in range(256)
        if b"I" in base64.b32encode(bytes([value]))
    )
    transcribed = encoded.replace(b"I", b"1")
    with pytest.raises(binascii.Error):
        base64.b32decode(transcribed)
    assert base64.b32decode(transcribed, map01=b"I") == payload


def test_extended_hex_base32_has_its_own_unambiguous_alphabet():
    encoded = base64.b32hexencode(b"Python 3.10")
    assert base64.b32hexdecode(encoded) == b"Python 3.10"
    assert base64.b32hexdecode(encoded.lower(), casefold=True) == b"Python 3.10"
    with pytest.raises(TypeError):
        base64.b32hexdecode(encoded, map01=b"I")
