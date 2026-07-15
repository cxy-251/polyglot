"""376｜标准/URL-safe Base64、替代字母表与严格校验。

现代接口把任意 bytes-like 编成 ASCII bytes，也接受 ASCII str 解码。URL-safe 只把 ``+ /`` 换成
``- _``，仍可能含 ``=`` padding，并不等于可直接去 padding 的 token 格式。b64decode 默认丢弃
非字母字符；安全边界应使用 validate=True，避免被插入的隐藏字符悄悄忽略。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.base64.b64encode
# polyglot-covers: python.base64.b64decode
# polyglot-covers: python.base64.standard_b64encode
# polyglot-covers: python.base64.standard_b64decode
# polyglot-covers: python.base64.urlsafe_b64encode
# polyglot-covers: python.base64.urlsafe_b64decode
# polyglot-covers: python.base64.altchars
# polyglot-covers: python.base64.altchars-length-two
# polyglot-covers: python.base64.encode-bytes-like-output-bytes
# polyglot-covers: python.base64.decode-ascii-str
# polyglot-covers: python.base64.urlsafe-still-has-padding
# polyglot-covers: python.base64.b64decode-validate-false-discards-nonalphabet
# polyglot-covers: python.base64.b64decode-validate-true-binascii-error
# polyglot-covers: python.base64.incorrect-padding-binascii-error

import base64
import binascii

import pytest


def test_standard_altchars_and_urlsafe_alphabets_round_trip_bytes_like_input():
    payload = memoryview(b"\xfb\xff")
    standard = base64.b64encode(payload)
    alternative = base64.b64encode(payload, altchars=b"-_")
    urlsafe = base64.urlsafe_b64encode(payload)

    assert standard == b"+/8="
    assert alternative == urlsafe == b"-_8="
    assert urlsafe.endswith(b"=")
    assert base64.standard_b64encode(payload) == standard
    assert base64.standard_b64decode(standard.decode("ascii")) == payload
    assert base64.b64decode(alternative, altchars="-_") == payload
    assert base64.urlsafe_b64decode(urlsafe.decode("ascii")) == payload


def test_validate_changes_nonalphabet_characters_from_ignored_to_error():
    disguised = b"c2Vj!!cmV0\n"  # 插入 ! 和换行后，宽松模式仍解成 secret。
    assert base64.b64decode(disguised) == b"secret"
    with pytest.raises(binascii.Error, match="Only base64 data"):
        base64.b64decode(disguised, validate=True)
    with pytest.raises(binascii.Error, match="padding"):
        base64.b64decode(b"YWJ")


def test_altchars_must_be_a_two_byte_alphabet_description():
    with pytest.raises((AssertionError, ValueError)):
        base64.b64encode(b"data", altchars=b"one")
    with pytest.raises(TypeError):
        base64.b64encode(b"data", altchars="-_")
