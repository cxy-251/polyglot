"""378｜Ascii85 与 Git-style Base85 的 framing、缩写、换行和 padding。

Ascii85 支持 btoa 的四空格缩写 ``y``、Adobe ``<~ ~>`` framing 和可选换行；解码端必须启用
对应 dialect。Base85 使用另一套字母表，不与 Ascii85 互换。默认编码短尾块可无损还原；显式
pad=True 把 NUL 变成真实输入的一部分，完整五字符组无法让解码器知道它原本是 padding。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.base64.a85encode
# polyglot-covers: python.base64.a85decode
# polyglot-covers: python.base64.ascii85-foldspaces-y
# polyglot-covers: python.base64.ascii85-wrapcol
# polyglot-covers: python.base64.ascii85-adobe-framing
# polyglot-covers: python.base64.ascii85-ignorechars
# polyglot-covers: python.base64.ascii85-pad
# polyglot-covers: python.base64.b85encode
# polyglot-covers: python.base64.b85decode
# polyglot-covers: python.base64.base85-short-tail-roundtrip
# polyglot-covers: python.base64.base85-explicit-padding-nul-trap
# polyglot-covers: python.base64.ascii85-base85-not-interchangeable

import base64

import pytest


def test_ascii85_dialect_options_must_match_during_decode():
    folded = base64.a85encode(b"    ", foldspaces=True)
    assert folded == b"y"
    with pytest.raises(ValueError):
        base64.a85decode(folded)
    assert base64.a85decode(folded, foldspaces=True) == b"    "

    framed = base64.a85encode(b"Adobe data", adobe=True, wrapcol=8)
    assert framed.startswith(b"<~")
    assert framed.rstrip().endswith(b"~>")
    assert all(len(line) <= 8 for line in framed.splitlines())
    assert base64.a85decode(framed, adobe=True) == b"Adobe data"
    encoded = base64.a85encode(b"Hello")
    with_whitespace = encoded[:3] + b" \n" + encoded[3:]
    assert base64.a85decode(with_whitespace, ignorechars=b" \n") == b"Hello"


def test_ascii85_padding_becomes_visible_nul_bytes_after_decode():
    encoded = base64.a85encode(b"abc", pad=True)
    assert len(encoded) == 5
    assert base64.a85decode(encoded) == b"abc\0"


def test_base85_short_tail_is_implicit_but_explicit_padding_is_data():
    compact = base64.b85encode(b"abc")
    padded = base64.b85encode(b"abc", pad=True)
    assert len(compact) == 4
    assert len(padded) == 5
    assert base64.b85decode(compact) == b"abc"
    assert base64.b85decode(padded) == b"abc\0"
    assert compact != base64.a85encode(b"abc")
