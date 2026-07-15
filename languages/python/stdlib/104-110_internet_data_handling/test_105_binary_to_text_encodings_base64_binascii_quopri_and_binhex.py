"""105｜标准/URL-safe Base64、替代字母表与严格校验。

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
import io
import quopri
import warnings

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
    # 不同 3.10 补丁版本使用过不同文案；稳定契约是抛 binascii.Error，而不是具体英文句子。
    with pytest.raises(binascii.Error, match="(?i)base64"):
        base64.b64decode(disguised, validate=True)
    with pytest.raises(binascii.Error, match="padding"):
        base64.b64decode(b"YWJ")


def test_altchars_must_be_a_two_byte_alphabet_description():
    with pytest.raises((AssertionError, ValueError)):
        base64.b64encode(b"data", altchars=b"one")
    with pytest.raises(TypeError):
        base64.b64encode(b"data", altchars="-_")


# Base16/Base32 大小写、易混字符与 Python 3.10 Base32hex。
#
# Base16/32 默认只接受规范大写。casefold=True 是兼容开关；Base32 的 map01 还可把 0 映射 O、把
# 1 映射 I 或 L，但默认因安全原因禁用，避免人眼凭据出现歧义。Extended Hex Base32 在 3.10 新增，
# 0/1 本就是其字母表成员，不能做上述替换。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# Ascii85 与 Git-style Base85 的 framing、缩写、换行和 padding。
#
# Ascii85 支持 btoa 的四空格缩写 ``y``、Adobe ``<~ ~>`` framing 和可选换行；解码端必须启用
# 对应 dialect。Base85 使用另一套字母表，不与 Ascii85 互换。默认编码短尾块可无损还原；显式
# pad=True 把 NUL 变成真实输入的一部分，完整五字符组无法让解码器知道它原本是 padding。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# Base64 legacy 文件接口与 RFC 2045 每行 76 字符。
#
# legacy encode/encodebytes 为 MIME 风格输出插入最多 76 字符的行并保证末尾换行；现代 b64encode
# 不换行。decode 从 binary input 的 readline 逐行消费并写 binary output，不接受现代接口支持的
# ASCII str。真正构造 MIME 邮件时应使用 email 包，让它同时维护 Content-Transfer-Encoding header。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.base64.encodebytes
# polyglot-covers: python.base64.decodebytes
# polyglot-covers: python.base64.encode-legacy-file-interface
# polyglot-covers: python.base64.decode-legacy-file-interface
# polyglot-covers: python.base64.legacy-binary-file-objects
# polyglot-covers: python.base64.legacy-rfc2045-line-length-76
# polyglot-covers: python.base64.legacy-output-trailing-newline
# polyglot-covers: python.base64.modern-output-no-line-wrap
# polyglot-covers: python.base64.prefer-email-package-for-mime



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


# binascii 的低层 UU、Base64 与 quoted-printable 转换。
#
# binascii 是 base64/quopri/uu 等高层模块的 C 加速底座。b2a_uu 每次最多处理 45 bytes 并总带
# 换行；b2a_base64 可关闭换行。a2b_* 可接收纯 ASCII str，而 b2a_* 要求 bytes-like。quoted-
# printable 的 header=True 会把 underscore 当作空格，这与正文模式不同。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# hexlify/unhexlify 的 separator 方向与增量 CRC。
#
# hexlify 返回长度恰为输入两倍的 bytes；bytes_per_sep 正数从右端分组，负数从左端分组，这对协议
# 字段布局很重要。unhexlify 要求纯十六进制且位数为偶数，比 bytes.fromhex 对空白更严格。crc32
# 和 crc_hqx 可用前一段结果作为下一段 seed，但它们是误码 checksum，不是抗碰撞密码学 hash。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# 已弃用的 BinHex HQX/RLE 底层原语与 Incomplete。
#
# Python 3.9 起 HQX/RLE 函数已弃用，但 3.10 仍保留供旧 BinHex 数据迁移。a2b_hqx 返回
# ``(data, done)``，冒号终止符才令 done 为真；RLE 的 0x90 是 repeat marker，孤立 marker 表示还
# 需更多输入并抛 Incomplete，而不是把损坏数据误报为一般编程错误。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.binascii.b2a_hqx
# polyglot-covers: python.binascii.a2b_hqx
# polyglot-covers: python.binascii.a2b-hqx-data-done-tuple
# polyglot-covers: python.binascii.rlecode_hqx
# polyglot-covers: python.binascii.rledecode_hqx
# polyglot-covers: python.binascii.hqx-rle-repeat-marker
# polyglot-covers: python.binascii.Incomplete
# polyglot-covers: python.binascii.incomplete-means-read-more-data
# polyglot-covers: python.binascii.hqx-primitives-deprecated-since-3.9




def test_hqx_ascii_conversion_reports_whether_the_end_marker_was_seen():
    # 不带 ``:`` 时，输入仍必须包含完整的 3-byte/4-character 编码量子；否则 Incomplete
    # 表示调用方还应继续喂数据，而不是“没有结束标记”的普通 done=0。
    payload = b"legacy-binhex!!"
    with pytest.warns(DeprecationWarning):
        encoded = binascii.b2a_hqx(payload)
    with pytest.warns(DeprecationWarning):
        decoded, done = binascii.a2b_hqx(encoded)
    assert decoded == payload
    assert done == 0

    with pytest.warns(DeprecationWarning):
        decoded, done = binascii.a2b_hqx(encoded + b":")
    assert decoded == payload
    assert done == 1


def test_hqx_rle_round_trip_and_orphaned_marker_incomplete_error():
    payload = b"AAAAA\x90\x90BBBBBBBB"
    with pytest.warns(DeprecationWarning):
        encoded = binascii.rlecode_hqx(payload)
    with pytest.warns(DeprecationWarning):
        assert binascii.rledecode_hqx(encoded) == payload
    with pytest.warns(DeprecationWarning):
        with pytest.raises(binascii.Incomplete):
            binascii.rledecode_hqx(b"orphan\x90")
    assert issubclass(binascii.Incomplete, Exception)


# quoted-printable 的正文/header 模式、行尾空白与 binary stream。
#
# quoted-printable 适合大部分可打印、少量 binary 的 MIME 内容。正文中行尾 space/tab 必须编码，
# quotetabs 决定中间空白是否编码；header=True 把空格变 ``_``，并把原 underscore 编为 ``=5F``。
# 长行用 ``=\n`` soft break 折行，解码时移除；流接口始终读写 binary file object。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# Python 3.10 已弃用 BinHex4 的文件迁移工作流。
#
# binhex 只保留 Macintosh 文件的 data fork，不保存 resource fork；文本还沿用旧 Mac CR 换行。
# 模块自 3.9 弃用，适合读取历史归档后迁往现代格式，不应成为新协议。binhex/hexbin 接受路径，
# hexbin(output=None) 则信任归档内文件名并写到当前目录，调用前必须选定隔离目录。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.binhex.deprecated-since-3.9
# polyglot-covers: python.binhex.binhex
# polyglot-covers: python.binhex.hexbin
# polyglot-covers: python.binhex.file-path-roundtrip
# polyglot-covers: python.binhex.data-fork-only
# polyglot-covers: python.binhex.hexbin-output-none-embedded-filename
# polyglot-covers: python.binhex.output-none-current-directory-trap
# polyglot-covers: python.binhex.Error


with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import binhex



def test_explicit_input_encoded_and_output_paths_round_trip_data_fork(tmp_path):
    source = tmp_path / "source.bin"
    archive = tmp_path / "archive.hqx"
    decoded = tmp_path / "decoded.bin"
    payload = bytes(range(256))
    source.write_bytes(payload)

    assert binhex.binhex(str(source), str(archive)) is None
    assert archive.read_bytes().startswith(b"(This file must be converted with BinHex")
    assert binhex.hexbin(str(archive), str(decoded)) is None
    assert decoded.read_bytes() == payload


def test_output_none_uses_embedded_name_inside_an_isolated_directory(tmp_path, monkeypatch):
    source = tmp_path / "embedded-name.bin"
    archive = tmp_path / "archive.hqx"
    source.write_bytes(b"legacy")
    binhex.binhex(str(source), str(archive))
    source.unlink()

    monkeypatch.chdir(tmp_path)
    binhex.hexbin(str(archive), None)
    assert source.read_bytes() == b"legacy"


def test_invalid_binhex_document_raises_module_specific_error(tmp_path):
    invalid = tmp_path / "invalid.hqx"
    invalid.write_bytes(b"not binhex")
    with pytest.raises(binhex.Error):
        binhex.hexbin(str(invalid), str(tmp_path / "ignored.bin"))
