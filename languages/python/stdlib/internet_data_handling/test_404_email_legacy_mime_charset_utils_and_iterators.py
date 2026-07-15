"""404｜legacy MIMEBase、MIMEMultipart 与 MIMENonMultipart。

email.mime 属于 compat32 API：MIMEBase 自动补 Content-Type 和 MIME-Version；multipart
把子消息保存在 list payload 中，并延迟生成 boundary；non-multipart 则主动禁止 attach。
现代代码通常优先使用 EmailMessage.set_content/add_attachment，但维护旧邮件代码仍需读懂这些类。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.mime.MIMEBase
# polyglot-covers: python.email.mime.MIMEBase-content-type-header
# polyglot-covers: python.email.mime.MIMEBase-mime-version-header
# polyglot-covers: python.email.mime.MIMEBase-params
# polyglot-covers: python.email.mime.MIMEMultipart
# polyglot-covers: python.email.mime.MIMEMultipart-subparts
# polyglot-covers: python.email.mime.MIMEMultipart-delayed-boundary
# polyglot-covers: python.email.mime.MIMEMultipart-attach
# polyglot-covers: python.email.mime.compat32-default-policy
# polyglot-covers: python.email.mime.MIMENonMultipart
# polyglot-covers: python.email.mime.nonmultipart-attach-error




from email import policy
from email.errors import MultipartConversionError
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.text import MIMEText
import pytest
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.mime.message import MIMEMessage
from email.encoders import encode_7or8bit, encode_base64, encode_noop, encode_quopri
from email.header import Header, decode_header, make_header
import base64
from email.charset import BASE64, SHORTEST, Charset
from email.header import decode_header
import email.charset as charset_module
from email.header import decode_header, make_header
from email.utils import formataddr, getaddresses, make_msgid, parseaddr, quote, unquote
import sys
from datetime import datetime, timedelta, timezone
from email.utils import (
    format_datetime,
    formatdate,
    localtime,
    mktime_tz,
    parsedate,
    parsedate_to_datetime,
    parsedate_tz,
)
from email.utils import (
    collapse_rfc2231_value,
    decode_params,
    decode_rfc2231,
    encode_rfc2231,
)
from email.iterators import _structure, body_line_iterator, typed_subpart_iterator
from io import StringIO

def test_mime_base_adds_required_headers_and_content_type_parameters():
    part = MIMEBase("application", "x-example", name="payload.bin")

    assert part.get_content_type() == "application/x-example"
    assert part.get_param("name") == "payload.bin"
    assert part["MIME-Version"] == "1.0"
    assert part.policy is policy.compat32


def test_multipart_keeps_subparts_and_generates_boundary_only_when_flattened():
    first = MIMEText("first")
    second = MIMEText("second", _subtype="html")
    container = MIMEMultipart(_subtype="alternative", _subparts=(first,))

    assert container.get_boundary() is None
    assert container.get_payload() == [first]
    container.attach(second)
    assert container.get_payload(1) is second

    # boundary 为 None 时不是非法状态；序列化器在真正需要 wire format 时才补上稳定值。
    wire = container.as_string()
    assert container.get_boundary() is not None
    assert container.get_boundary() in wire


def test_nonmultipart_rejects_attach_instead_of_silently_corrupting_payload_shape():
    scalar = MIMENonMultipart("text", "plain")
    with pytest.raises(MultipartConversionError):
        scalar.attach(MIMEText("child"))


# 405｜MIMEApplication、MIMEImage、MIMEAudio、MIMEMessage 等便捷类。
#
# 专用 MIME 类设置 maintype/subtype，并默认以 base64 编码二进制数据。图片和音频可尝试
# 从内容猜 subtype，但不认识的字节必须显式给出 subtype；MIMEMessage 的 payload 必须是
# Message。_encoder 是扩展点，负责同时改 payload 和 Content-Transfer-Encoding header。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.mime.MIMEApplication
# polyglot-covers: python.email.mime.MIMEApplication-default-subtype
# polyglot-covers: python.email.mime.specialized-default-base64
# polyglot-covers: python.email.mime.MIMEImage
# polyglot-covers: python.email.mime.MIMEImage-explicit-subtype
# polyglot-covers: python.email.mime.MIMEImage-undetectable-type-error
# polyglot-covers: python.email.mime.MIMEAudio
# polyglot-covers: python.email.mime.MIMEAudio-explicit-subtype
# polyglot-covers: python.email.mime.MIMEAudio-undetectable-type-error
# polyglot-covers: python.email.mime.MIMEMessage
# polyglot-covers: python.email.mime.MIMEMessage-message-only
# polyglot-covers: python.email.mime.custom-encoder-protocol




def test_binary_mime_classes_set_types_and_default_to_base64():
    raw = b"\x00\xffpayload"
    application = MIMEApplication(raw)
    image = MIMEImage(raw, _subtype="x-demo")
    audio = MIMEAudio(raw, _subtype="x-demo")

    assert application.get_content_type() == "application/octet-stream"
    assert image.get_content_type() == "image/x-demo"
    assert audio.get_content_type() == "audio/x-demo"
    for part in (application, image, audio):
        assert part["Content-Transfer-Encoding"] == "base64"
        assert part.get_payload(decode=True) == raw


def test_image_and_audio_require_a_subtype_when_the_bytes_are_not_recognized():
    with pytest.raises(TypeError):
        MIMEImage(b"not an image")
    with pytest.raises(TypeError):
        MIMEAudio(b"not audio")


def test_mime_message_wraps_a_message_and_rejects_arbitrary_payloads():
    inner = Message()
    inner["Subject"] = "nested"
    wrapped = MIMEMessage(inner)

    assert wrapped.get_content_type() == "message/rfc822"
    assert wrapped.is_multipart() is True
    assert wrapped.get_payload() == [inner]
    with pytest.raises(TypeError):
        MIMEMessage("not a Message")


def test_specialized_class_accepts_a_custom_encoder_protocol():
    def encode_as_hex(message):
        raw = message.get_payload(decode=True)
        message.set_payload(raw.hex())
        message["Content-Transfer-Encoding"] = "x-hex"

    part = MIMEApplication(b"\x00\xff", _encoder=encode_as_hex)
    assert part.get_payload() == "00ff"
    assert part["Content-Transfer-Encoding"] == "x-hex"


# 406｜MIMEText 的 charset 推断，以及已有 CTE header 带来的旧 API 陷阱。
#
# 纯 ASCII 文本默认 us-ascii，非 ASCII 文本默认 utf-8，并会生成对应传输编码。一个容易忽略的
# 兼容行为是：已有 Content-Transfer-Encoding 时，set_payload(..., charset=...) 假定 payload
# 已正确编码而不再转换。若要重新编码，必须先删除旧 CTE header，或改用现代 set_content。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.mime.MIMEText
# polyglot-covers: python.email.mime.MIMEText-default-subtype
# polyglot-covers: python.email.mime.MIMEText-ascii-charset
# polyglot-covers: python.email.mime.MIMEText-unicode-utf8-charset
# polyglot-covers: python.email.mime.MIMEText-content-transfer-encoding
# polyglot-covers: python.email.mime.MIMEText-existing-cte-prevents-reencoding
# polyglot-covers: python.email.mime.MIMEText-delete-cte-before-reencoding



def test_mimetext_selects_ascii_or_utf8_and_preserves_decoded_content():
    ascii_part = MIMEText("plain text")
    unicode_part = MIMEText("中文")

    assert ascii_part.get_content_type() == "text/plain"
    assert ascii_part.get_content_charset() == "us-ascii"
    assert ascii_part["Content-Transfer-Encoding"] == "7bit"
    assert unicode_part.get_content_charset() == "utf-8"
    assert unicode_part.get_payload(decode=True) == "中文".encode()


def test_existing_transfer_encoding_must_be_removed_before_set_payload_reencodes():
    part = MIMEText("first", _charset="utf-8")
    assert part["Content-Transfer-Encoding"] == "base64"

    # 旧 CTE 仍在时，新字符串被原样放入 payload；header 与实际内容已经不一致。
    part.set_payload("second", charset="utf-8")
    assert part.get_payload() == "second"

    del part["Content-Transfer-Encoding"]
    part.set_payload("second", charset="utf-8")
    assert part["Content-Transfer-Encoding"] == "base64"
    assert part.get_payload() != "second"
    assert part.get_payload(decode=True) == b"second"


# 407｜email.encoders 的 base64、quoted-printable、7bit/8bit 与 noop。
#
# 这些函数原地读取 Message payload、写回传输形式并设置 CTE header；multipart 没有单一 payload，
# 因此必须对子 part 编码而不能对容器编码。它们属于已弃用的 compat32 API，现代代码应通过
# set_content(..., cte=...) 选择编码，但旧消息构造器仍在内部使用相同协议。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.encoders.encode_base64
# polyglot-covers: python.email.encoders.encode_quopri
# polyglot-covers: python.email.encoders.encode-quopri-encodes-whitespace
# polyglot-covers: python.email.encoders.encode_7or8bit
# polyglot-covers: python.email.encoders.encode-7or8bit-ascii
# polyglot-covers: python.email.encoders.encode-7or8bit-nonascii
# polyglot-covers: python.email.encoders.encode_noop
# polyglot-covers: python.email.encoders.multipart-type-error
# polyglot-covers: python.email.encoders.deprecated-modern-cte-alternative




def message_with_bytes(payload):
    message = Message()
    message.set_payload(payload)
    return message


def test_base64_and_quoted_printable_encoders_round_trip_binary_payloads():
    raw = b"data\x00 with\tspace "
    base64_message = message_with_bytes(raw)
    quoted_message = message_with_bytes(raw)

    encode_base64(base64_message)
    encode_quopri(quoted_message)

    assert base64_message["Content-Transfer-Encoding"] == "base64"
    assert quoted_message["Content-Transfer-Encoding"] == "quoted-printable"
    assert base64_message.get_payload(decode=True) == raw
    assert quoted_message.get_payload(decode=True) == raw
    # legacy quoted-printable encoder 连普通空格和 tab 也编码，不能期待人类可读性完全不变。
    assert "=09" in quoted_message.get_payload()
    assert "=20" in quoted_message.get_payload()


def test_7or8bit_inspects_ascii_decodability_while_noop_changes_nothing():
    ascii_message = message_with_bytes(b"ASCII")
    binary_message = message_with_bytes(b"\xff")
    untouched = message_with_bytes(b"raw")

    encode_7or8bit(ascii_message)
    encode_7or8bit(binary_message)
    encode_noop(untouched)

    assert ascii_message["Content-Transfer-Encoding"] == "7bit"
    assert binary_message["Content-Transfer-Encoding"] == "8bit"
    assert untouched.get_payload() == b"raw"
    assert untouched["Content-Transfer-Encoding"] is None


def test_encoder_must_be_applied_to_leaf_parts_not_a_multipart_container():
    with pytest.raises(TypeError):
        encode_base64(MIMEMultipart())


# 408｜legacy Header 的多字符集片段、折行、解码与重建。
#
# Header 用 RFC 2047 encoded-word 把非 ASCII 标题放进 7-bit 邮件头；append 可声明 bytes 的
# 源字符集，encode 控制线长与换行符，decode_header 则只拆成 bytes/charset 对而不替调用方
# 统一解码。现代 EmailMessage 会自动完成这些工作，Header 主要用于旧代码或精确编码控制。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# 409｜Charset 的规范化、编码策略与按行 header 编码。
#
# Charset 不是通用文本编解码器，而是 legacy email 的字符集策略对象：它记录输入/输出 codec、
# header/body 的传输编码和输出 charset。utf-8 header 可在 QP/base64 中选较短者，body 固定
# base64；us-ascii 则保持 7bit。多字节 header 应使用 header_encode_lines 避免在字节中间切断。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# 410｜email.charset 的全局 alias、字符集策略与 codec 注册表。
#
# add_alias/add_charset/add_codec 会修改模块级注册表，影响之后构造的每个 Charset；这类全局状态
# 在测试和长进程中很容易泄漏。本文件用 monkeypatch 替换为副本后再演示注册流程。SHORTEST
# 只允许用于 header，body 必须选择明确编码或不编码。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.charset.add_alias
# polyglot-covers: python.email.charset.ALIASES-registry
# polyglot-covers: python.email.charset.add_charset
# polyglot-covers: python.email.charset.CHARSETS-registry
# polyglot-covers: python.email.charset.add_codec
# polyglot-covers: python.email.charset.CODEC_MAP-registry
# polyglot-covers: python.email.charset.QP
# polyglot-covers: python.email.charset.BASE64
# polyglot-covers: python.email.charset.SHORTEST
# polyglot-covers: python.email.charset.shortest-not-valid-for-body
# polyglot-covers: python.email.charset.global-registry-isolation




def isolate_registries(monkeypatch):
    monkeypatch.setattr(charset_module, "ALIASES", dict(charset_module.ALIASES))
    monkeypatch.setattr(charset_module, "CHARSETS", dict(charset_module.CHARSETS))
    monkeypatch.setattr(charset_module, "CODEC_MAP", dict(charset_module.CODEC_MAP))


def test_custom_alias_charset_and_codec_form_one_resolution_pipeline(monkeypatch):
    isolate_registries(monkeypatch)
    charset_module.add_alias("x-demo-alias", "x-demo")
    charset_module.add_charset(
        "x-demo",
        charset_module.QP,
        charset_module.BASE64,
        "utf-8",
    )
    charset_module.add_codec("x-demo", "utf-8")

    configured = charset_module.Charset("x-demo-alias")
    assert configured.input_charset == "x-demo"
    assert configured.output_charset == "utf-8"
    assert configured.header_encoding == charset_module.QP
    assert configured.body_encoding == charset_module.BASE64
    assert configured.input_codec == "utf-8"
    assert configured.output_codec == "utf-8"


def test_shortest_strategy_is_rejected_for_message_bodies(monkeypatch):
    isolate_registries(monkeypatch)
    with pytest.raises(ValueError, match="SHORTEST"):
        charset_module.add_charset(
            "x-invalid",
            charset_module.QP,
            charset_module.SHORTEST,
        )


# 411｜compat32 Message 的 Unix-From、list payload 与 set_charset。
#
# Message 的 payload 可能是标量，也可能是子 Message 列表；is_multipart 判断的是实际 list 形状，
# 不只是 Content-Type 文本。attach 从 None 建立 list，get_payload 返回的 list 是活对象。旧式
# set_charset 会补 MIME headers 并编码 payload，现代 EmailMessage 则应使用 set_content。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.compat32.Message
# polyglot-covers: python.email.compat32.Message-default-policy
# polyglot-covers: python.email.compat32.set_unixfrom
# polyglot-covers: python.email.compat32.get_unixfrom
# polyglot-covers: python.email.compat32.as_string-unixfrom
# polyglot-covers: python.email.compat32.as_bytes-unixfrom
# polyglot-covers: python.email.compat32.attach-list-payload
# polyglot-covers: python.email.compat32.get_payload-index
# polyglot-covers: python.email.compat32.get-payload-live-list
# polyglot-covers: python.email.compat32.get-payload-scalar-index-typeerror
# polyglot-covers: python.email.compat32.get-payload-decode-multipart-none
# polyglot-covers: python.email.compat32.set_payload
# polyglot-covers: python.email.compat32.set_charset
# polyglot-covers: python.email.compat32.get_charset
# polyglot-covers: python.email.compat32.set-charset-none-removes-param




def test_unixfrom_is_envelope_metadata_and_only_serializes_when_requested():
    message = Message()
    message["Subject"] = "example"
    message.set_payload("body")
    message.set_unixfrom("From sender@example.test Sat Jan  1 00:00:00 2000")

    assert message.policy is policy.compat32
    assert message.get_unixfrom().startswith("From sender@example.test")
    assert not message.as_string().startswith("From ")
    assert message.as_string(unixfrom=True).startswith("From sender@example.test")
    assert message.as_bytes(unixfrom=True).startswith(b"From sender@example.test")


def test_attach_creates_a_live_list_payload_with_indexed_access():
    container = Message()
    first = Message()
    second = Message()
    container.attach(first)

    assert container.is_multipart() is True
    assert container.get_payload(0) is first
    payload = container.get_payload()
    payload.append(second)
    assert container.get_payload(1) is second
    assert container.get_payload(decode=True) is None

    scalar = Message()
    scalar.set_payload("text")
    with pytest.raises(TypeError):
        scalar.get_payload(0)


def test_set_charset_adds_mime_metadata_encodes_payload_and_can_remove_parameter():
    message = Message()
    message.set_payload("café")
    message.set_charset("utf-8")

    assert message.get_charset().input_charset == "utf-8"
    assert message["MIME-Version"] == "1.0"
    assert message.get_content_type() == "text/plain"
    assert message.get_content_charset() == "utf-8"
    assert message.get_payload(decode=True) == "café".encode()

    message.set_charset(None)
    assert message.get_charset() is None
    assert message.get_content_charset() is None


# 412｜email.utils 的 Message-ID、地址拆装与引号转义。
#
# make_msgid 在显式 domain 下仍为每次调用生成唯一值。quote/unquote 只处理邮件语法引号，不是
# 任意转义器。parseaddr/getaddresses 是 compat32 字符串解析器；3.10.15 起默认 strict=True，
# 会拒绝畸形输入。结构化 headerregistry.Address 是新代码更可靠的选择。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.utils.make_msgid
# polyglot-covers: python.email.utils.make-msgid-domain
# polyglot-covers: python.email.utils.make-msgid-idstring
# polyglot-covers: python.email.utils.make-msgid-uniqueness
# polyglot-covers: python.email.utils.quote
# polyglot-covers: python.email.utils.unquote
# polyglot-covers: python.email.utils.parseaddr
# polyglot-covers: python.email.utils.parseaddr-strict-3.10.15
# polyglot-covers: python.email.utils.formataddr
# polyglot-covers: python.email.utils.formataddr-international-name
# polyglot-covers: python.email.utils.getaddresses



def test_message_ids_use_requested_components_but_remain_unique():
    first = make_msgid(idstring="worker", domain="example.test")
    second = make_msgid(idstring="worker", domain="example.test")

    assert first.startswith("<") and first.endswith(".worker@example.test>")
    assert second.startswith("<") and second.endswith(".worker@example.test>")
    assert first != second


def test_quote_unquote_and_address_formatting_are_email_specific_operations():
    escaped = quote('path\\name "label"')
    assert escaped == 'path\\\\name \\"label\\"'
    assert unquote(f'"{escaped}"') == 'path\\name "label"'
    assert unquote("<user@example.test>") == "user@example.test"

    rendered = formataddr(("张三", "zhang@example.test"), charset="utf-8")
    encoded_name, address = parseaddr(rendered)
    assert address == "zhang@example.test"
    assert str(make_header(decode_header(encoded_name))) == "张三"


def test_parseaddr_and_getaddresses_handle_single_and_multiple_header_values():
    assert parseaddr("Alice <alice@example.test>") == (
        "Alice",
        "alice@example.test",
    )
    assert getaddresses(
        ["Alice <alice@example.test>, bob@example.test", "Carol <c@example.test>"]
    ) == [
        ("Alice", "alice@example.test"),
        ("", "bob@example.test"),
        ("Carol", "c@example.test"),
    ]

    if sys.version_info >= (3, 10, 15):
        malformed = "alice@example.test <bob@example.test>"
        assert parseaddr(malformed) == ("", "")
        assert parseaddr(malformed, strict=False) != ("", "")


# 413｜RFC 2822 日期解析、格式化、时区偏移与本地时区转换。
#
# parsedate 返回兼容 time.mktime 的 9 元组，但末三项不可靠；parsedate_tz 另加相对 UTC 的秒数，
# mktime_tz 将其规范化成 UTC timestamp。-0000 表示“UTC 时间但来源时区未知”，因此解析成
# naive datetime；+0000/GMT 才保留 aware UTC。测试只用固定时间，不读取当前时钟。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.utils.parsedate
# polyglot-covers: python.email.utils.parsedate-invalid-none
# polyglot-covers: python.email.utils.parsedate_tz
# polyglot-covers: python.email.utils.parsedate-tz-offset-seconds
# polyglot-covers: python.email.utils.parsedate_to_datetime
# polyglot-covers: python.email.utils.parsedate-minus-zero-naive
# polyglot-covers: python.email.utils.parsedate-invalid-valueerror
# polyglot-covers: python.email.utils.mktime_tz
# polyglot-covers: python.email.utils.formatdate
# polyglot-covers: python.email.utils.formatdate-usegmt
# polyglot-covers: python.email.utils.format_datetime
# polyglot-covers: python.email.utils.format-datetime-naive-minus-zero
# polyglot-covers: python.email.utils.format-datetime-aware-offset
# polyglot-covers: python.email.utils.localtime
# polyglot-covers: python.email.utils.localtime-preserves-instant




def test_parse_date_variants_expose_calendar_fields_and_timezone_seconds():
    text = "Mon, 20 Nov 1995 19:12:08 -0500"
    basic = parsedate(text)
    with_zone = parsedate_tz(text)

    assert basic[:6] == (1995, 11, 20, 19, 12, 8)
    assert with_zone[:6] == basic[:6]
    assert with_zone[9] == -5 * 60 * 60
    expected = datetime(1995, 11, 21, 0, 12, 8, tzinfo=timezone.utc).timestamp()
    assert mktime_tz(with_zone) == expected
    assert parsedate("not a date") is None


def test_datetime_parser_distinguishes_unknown_from_explicit_utc_zone():
    unknown_zone = parsedate_to_datetime("Tue, 02 Jan 2024 03:04:05 -0000")
    explicit_utc = parsedate_to_datetime("Tue, 02 Jan 2024 03:04:05 +0000")

    assert unknown_zone.tzinfo is None
    assert explicit_utc.tzinfo == timezone.utc
    with pytest.raises(ValueError):
        parsedate_to_datetime("Tue, 02 Jan 2024 25:04:05 +0000")


def test_fixed_timestamps_and_datetimes_format_without_reading_current_time():
    assert formatdate(1_000_000_000, usegmt=True) == (
        "Sun, 09 Sep 2001 01:46:40 GMT"
    )
    assert formatdate(1_000_000_000).endswith("-0000")

    naive = datetime(2024, 1, 2, 3, 4, 5)
    east_eight = naive.replace(tzinfo=timezone(timedelta(hours=8)))
    utc = naive.replace(tzinfo=timezone.utc)
    assert format_datetime(naive).endswith("-0000")
    assert format_datetime(east_eight).endswith("+0800")
    assert format_datetime(utc, usegmt=True).endswith("GMT")


def test_localtime_converts_zone_but_preserves_the_instant():
    instant = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    converted = localtime(instant)

    assert converted.tzinfo is not None
    assert converted.timestamp() == instant.timestamp()


# 414｜RFC 2231 参数的编码、分段解码与最终 Unicode 折叠。
#
# 邮件参数用 charset'language'percent-encoded 形式承载非 ASCII filename。decode_rfc2231 只拆
# charset/language/value，不负责 percent decoding；decode_params 会合并带 * 的连续参数，最后
# 由 collapse_rfc2231_value 按声明字符集生成 str。不要把任一中间元组直接展示给用户。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.utils.encode_rfc2231
# polyglot-covers: python.email.utils.encode-rfc2231-charset-language
# polyglot-covers: python.email.utils.decode_rfc2231
# polyglot-covers: python.email.utils.decode-rfc2231-does-not-percent-decode
# polyglot-covers: python.email.utils.decode_params
# polyglot-covers: python.email.utils.decode-params-star-parameter
# polyglot-covers: python.email.utils.collapse_rfc2231_value
# polyglot-covers: python.email.utils.collapse-rfc2231-nontuple-unquotes



def test_rfc2231_encoder_and_low_level_decoder_keep_declared_metadata():
    encoded = encode_rfc2231("résumé.pdf", charset="utf-8", language="fr")
    assert encoded == "utf-8'fr'r%C3%A9sum%C3%A9.pdf"

    # 这里第三项仍是 percent-encoded；decode_rfc2231 的职责只是拆三段。
    assert decode_rfc2231(encoded) == (
        "utf-8",
        "fr",
        "r%C3%A9sum%C3%A9.pdf",
    )


def test_decode_params_and_collapse_form_the_complete_unicode_pipeline():
    decoded = decode_params(
        [
            ("attachment", ""),
            ("filename*", "utf-8''r%C3%A9sum%C3%A9.pdf"),
        ]
    )

    assert decoded[0] == ("attachment", "")
    name, structured_value = decoded[1]
    assert name == "filename"
    assert collapse_rfc2231_value(structured_value) == "résumé.pdf"
    assert collapse_rfc2231_value('"plain.txt"') == "plain.txt"


# 415｜email.iterators 的 body 行、MIME 类型筛选与结构调试输出。
#
# body_line_iterator 深度遍历后只展开 str payload，跳过 header 和 bytes payload；
# typed_subpart_iterator 按 maintype/subtype 过滤 walk 结果。_structure 很适合人工诊断 MIME 树，
# 但官方明确把它标为不受支持的私有调试接口，业务逻辑不能依赖其文本格式。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.iterators.body_line_iterator
# polyglot-covers: python.email.iterators.body-line-iterator-skips-headers
# polyglot-covers: python.email.iterators.body-line-iterator-skips-bytes-payload
# polyglot-covers: python.email.iterators.body-line-iterator-line-boundaries
# polyglot-covers: python.email.iterators.typed_subpart_iterator
# polyglot-covers: python.email.iterators.typed-subpart-maintype-default
# polyglot-covers: python.email.iterators.typed-subpart-subtype-filter
# polyglot-covers: python.email.iterators._structure
# polyglot-covers: python.email.iterators.structure-private-debug-interface



def build_message_tree():
    root = MIMEMultipart()
    root.attach(MIMEText("plain one\nplain two", _subtype="plain"))
    root.attach(MIMEText("<p>html</p>", _subtype="html"))
    binary = Message()
    binary["Content-Type"] = "application/octet-stream"
    binary.set_payload(b"\x00\xff")
    root.attach(binary)
    return root


def test_body_line_iterator_yields_string_payload_lines_not_headers_or_bytes():
    lines = list(body_line_iterator(build_message_tree()))
    assert lines == ["plain one\n", "plain two", "<p>html</p>"]


def test_typed_iterator_filters_by_main_type_and_optional_subtype():
    root = build_message_tree()
    text_parts = list(typed_subpart_iterator(root))
    html_parts = list(typed_subpart_iterator(root, subtype="html"))

    assert [part.get_content_subtype() for part in text_parts] == ["plain", "html"]
    assert html_parts == [text_parts[1]]


def test_structure_prints_an_indented_debug_view_to_a_supplied_stream():
    output = StringIO()
    _structure(build_message_tree(), fp=output)

    assert output.getvalue().splitlines() == [
        "multipart/mixed",
        "    text/plain",
        "    text/html",
        "    application/octet-stream",
    ]
