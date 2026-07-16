"""108｜BytesParser/Parser、top-level convenience 与 header-only 快路径。

完整消息优先用 binary parser，并显式传 policy.default，才能得到 EmailMessage 与结构化 header；
不传 policy 在 3.10 仍默认为 compat32/Message，未来会改变。HeaderParser 只解析 header，把整个 MIME
body 留作原始 payload，适合只做路由信息但不能据此判断真实 multipart 子树。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.email.parser.BytesParser
# polyglot-covers: python.email.parser.BytesParser.parse
# polyglot-covers: python.email.parser.BytesParser.parsebytes
# polyglot-covers: python.email.parser.Parser
# polyglot-covers: python.email.parser.Parser.parse
# polyglot-covers: python.email.parser.Parser.parsestr
# polyglot-covers: python.email.parser.BytesHeaderParser
# polyglot-covers: python.email.parser.HeaderParser
# polyglot-covers: python.email.header-only-parser-raw-body
# polyglot-covers: python.email.message_from_bytes
# polyglot-covers: python.email.message_from_binary_file
# polyglot-covers: python.email.message_from_string
# polyglot-covers: python.email.message_from_file
# polyglot-covers: python.email.parser-explicit-policy-required
# polyglot-covers: python.email.parser-default-compat32-trap
# polyglot-covers: python.email.parser-policy-message-factory



import email
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesHeaderParser, BytesParser, HeaderParser, Parser
import io
from email.message import EmailMessage
from email.parser import BytesFeedParser, FeedParser
from email.generator import BytesGenerator, Generator
from email.generator import BytesGenerator, DecodedGenerator
from email.parser import BytesParser
from email import errors, policy
import pytest
from datetime import datetime, timedelta, timezone
from email.headerregistry import Address, BaseHeader, Group
from email.headerregistry import (
    BaseHeader,
    HeaderRegistry,
    UniqueUnstructuredHeader,
)

SIMPLE_BYTES = b"From: sender@example.test\r\nSubject: hello\r\n\r\nbody\r\n"


def test_binary_and_text_parsers_accept_whole_values_or_file_objects():
    byte_parser = BytesParser(policy=policy.default)
    from_bytes = byte_parser.parsebytes(bytearray(SIMPLE_BYTES))
    from_binary_file = byte_parser.parse(io.BytesIO(SIMPLE_BYTES))
    assert isinstance(from_bytes, EmailMessage)
    assert from_bytes.get_content() == "body\r\n"
    assert from_binary_file.as_bytes() == from_bytes.as_bytes()

    # parsebytes 在 3.10 直接调用输入的 decode；memoryview 虽是 bytes-like，却没有该方法。
    with pytest.raises(AttributeError, match="decode"):
        byte_parser.parsebytes(memoryview(SIMPLE_BYTES))

    text = SIMPLE_BYTES.decode("ascii")
    text_parser = Parser(policy=policy.default)
    assert text_parser.parsestr(text).get_content() == "body\r\n"
    assert text_parser.parse(io.StringIO(text)).get_content() == "body\r\n"


def test_top_level_conveniences_parallel_the_four_parser_entry_points():
    text = SIMPLE_BYTES.decode("ascii")
    messages = [
        email.message_from_bytes(SIMPLE_BYTES, policy=policy.default),
        email.message_from_binary_file(io.BytesIO(SIMPLE_BYTES), policy=policy.default),
        email.message_from_string(text, policy=policy.default),
        email.message_from_file(io.StringIO(text), policy=policy.default),
    ]
    assert all(isinstance(message, EmailMessage) for message in messages)
    assert [str(message["Subject"]) for message in messages] == ["hello"] * 4

    compat = BytesParser().parsebytes(SIMPLE_BYTES)
    assert type(compat) is Message
    assert compat.policy is policy.compat32


def test_header_only_parser_does_not_build_multipart_subparts():
    raw = (
        b"Content-Type: multipart/mixed; boundary=demo\r\n\r\n"
        b"--demo\r\nContent-Type: text/plain\r\n\r\npart\r\n--demo--\r\n"
    )
    full = BytesParser(policy=policy.default).parsebytes(raw)
    headers_only = BytesHeaderParser(policy=policy.default).parsebytes(raw)
    assert full.is_multipart() is True
    assert headers_only.is_multipart() is False
    assert isinstance(headers_only.get_payload(), str)
    assert "--demo" in headers_only.get_payload()

    text_headers = HeaderParser(policy=policy.default).parsestr(raw.decode("ascii"))
    assert text_headers.is_multipart() is False


# BytesFeedParser/FeedParser 的任意 chunk 边界与 close 语义。
#
# 增量 parser 可接收 partial line、混合 CR/LF/CRLF，并把跨 chunk 的 header/body 拼回同一语义；
# 只有 close 才返回根消息。适合 socket 等阻塞来源，但 feed 本身不负责网络读取。_factory 每创建
# 一个 root 或 MIME subpart 调用一次；显式 policy 仍决定 header 与 message 类型。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.email.parser.BytesFeedParser
# polyglot-covers: python.email.parser.FeedParser
# polyglot-covers: python.email.feedparser.feed
# polyglot-covers: python.email.feedparser.close
# polyglot-covers: python.email.feedparser-partial-lines
# polyglot-covers: python.email.feedparser-mixed-line-endings
# polyglot-covers: python.email.feedparser-arbitrary-chunk-boundaries
# polyglot-covers: python.email.feedparser-policy
# polyglot-covers: python.email.feedparser-factory-per-message-part
# polyglot-covers: python.email.feedparser-close-returns-root



RAW = (
    b"Subject: chunked\r\nContent-Type: multipart/mixed; boundary=x\n\r\n"
    b"--x\r\nContent-Type: text/plain\n\nfirst part\r\n--x--\n"
)


def test_bytes_feed_parser_stitches_partial_lines_and_mixed_endings():
    parser = BytesFeedParser(policy=policy.default)
    cuts = (1, 7, 19, 38, 57, len(RAW))
    start = 0
    for end in cuts:
        assert parser.feed(RAW[start:end]) is None
        start = end

    message = parser.close()
    assert isinstance(message, EmailMessage)
    assert str(message["Subject"]) == "chunked"
    assert message.is_multipart() is True
    assert list(message.iter_parts())[0].get_content().strip() == "first part"


def test_factory_is_used_for_root_and_each_mime_subpart():
    created = []

    def factory():
        message = EmailMessage(policy=policy.default)
        created.append(message)
        return message

    parser = BytesFeedParser(_factory=factory, policy=policy.default)
    parser.feed(RAW)
    root = parser.close()
    assert root is created[0]
    assert len(created) == 2
    assert list(root.iter_parts())[0] is created[1]


def test_text_feed_parser_accepts_str_but_is_best_reserved_for_ascii_messages():
    parser = FeedParser(policy=policy.default)
    parser.feed("Subject: text\n\nbo")
    parser.feed("dy\n")
    message = parser.close()
    assert isinstance(message, EmailMessage)
    assert message.get_content() == "body\n"


# BytesGenerator/Generator 的 stream 类型、From_ mangling 与 clone。
#
# BytesGenerator 写 binary stream，Generator 写 text stream；前者能保留 8-bit 数据，通常更适合
# 邮件。mangle_from_=True 只转义正文行首精确的 ``From ``，供 mbox 使用。flatten 可覆盖 unixfrom
# 和 linesep；clone 保留所有生成选项但换用独立 output stream，适合递归/并行目标。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.email.generator.BytesGenerator
# polyglot-covers: python.email.generator.BytesGenerator.flatten
# polyglot-covers: python.email.generator.BytesGenerator.write
# polyglot-covers: python.email.generator.Generator
# polyglot-covers: python.email.generator.Generator.flatten
# polyglot-covers: python.email.generator.Generator.write
# polyglot-covers: python.email.generator-binary-versus-text-stream
# polyglot-covers: python.email.generator.mangle_from
# polyglot-covers: python.email.generator.flatten-linesep-override
# polyglot-covers: python.email.generator.flatten-unixfrom
# polyglot-covers: python.email.generator.clone
# polyglot-covers: python.email.bytes-generator-surrogateescape-write



def _message_with_from_line():
    message = EmailMessage()
    message["Subject"] = "mbox body"
    message.set_content("first\nFrom danger\nlast\n")
    message.set_unixfrom("From sender@example.test Sat Jan  1 00:00:00 2022")
    return message


def test_bytes_generator_controls_envelope_mangling_and_line_separator():
    output = io.BytesIO()
    generator = BytesGenerator(output, mangle_from_=True, policy=policy.default)
    generator.flatten(_message_with_from_line(), unixfrom=True, linesep="\r\n")
    rendered = output.getvalue()
    assert rendered.startswith(b"From sender@example.test")
    assert b"\r\n>From danger\r\n" in rendered
    assert b"\n" not in rendered.replace(b"\r\n", b"")

    second = io.BytesIO()
    clone = generator.clone(second)
    clone.flatten(_message_with_from_line(), unixfrom=False, linesep="\r\n")
    assert not second.getvalue().startswith(b"From sender@example.test")
    assert b"\r\n>From danger\r\n" in second.getvalue()


def test_text_generator_writes_str_and_bytes_generator_restores_surrogate_bytes():
    text_output = io.StringIO()
    text_generator = Generator(text_output, mangle_from_=False, policy=policy.default)
    text_generator.flatten(_message_with_from_line())
    assert "\nFrom danger\n" in text_output.getvalue()
    text_generator.write("tail")
    assert text_output.getvalue().endswith("tail")

    binary_output = io.BytesIO()
    BytesGenerator(binary_output).write("\udcff")
    assert binary_output.getvalue() == b"\xff"


# 非变换 policy 的 bytes roundtrip 与 DecodedGenerator 人类视图。
#
# BytesParser + BytesGenerator 在相同、非变换 policy 下以字节往返为目标；默认 refold_source=long
# 可能重折长 header，所以需要原样签名/归档时应显式选择 refold_source=none。DecodedGenerator 不
# 生成可发送 MIME：它解码 text，并用模板占位非文本 part，适合日志或终端摘要。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.email.bytes-parser-generator-roundtrip
# polyglot-covers: python.email.policy.refold_source
# polyglot-covers: python.email.nontransforming-policy-workflow
# polyglot-covers: python.email.generator.DecodedGenerator
# polyglot-covers: python.email.decoded-generator-text-decoded
# polyglot-covers: python.email.decoded-generator-nontext-template
# polyglot-covers: python.email.decoded-generator-not-wire-format



def test_parse_and_generate_preserve_a_compliant_stream_with_nonrefolding_policy():
    raw = (
        b"From: sender@example.test\r\n"
        b"To: receiver@example.test\r\n"
        b"Subject: stable\r\n\r\n"
        b"body\r\n"
    )
    stable = policy.default.clone(refold_source="none", linesep="\r\n")
    message = BytesParser(policy=stable).parsebytes(raw)
    output = io.BytesIO()
    BytesGenerator(output, policy=stable).flatten(message)
    assert output.getvalue() == raw


def test_decoded_generator_replaces_binary_attachment_with_metadata_template():
    message = EmailMessage()
    message["Subject"] = "summary"
    message.set_content("readable body")
    message.add_attachment(
        b"\x00\xff",
        maintype="application",
        subtype="octet-stream",
        filename="data.bin",
    )

    output = io.StringIO()
    generator = DecodedGenerator(
        output,
        fmt="[omitted %(type)s filename=%(filename)s encoding=%(encoding)s]",
        policy=policy.default,
    )
    generator.flatten(message)
    rendered = output.getvalue()
    assert "readable body" in rendered
    assert "[omitted application/octet-stream filename=data.bin encoding=base64]" in rendered


# 宽容 parser 的 defects、延迟 Base64 defect 与 raise_on_defect。
#
# Feed parser 尽力保留不合规邮件，并把问题登记在实际出错 part 的 defects；调用者不能把“成功返回
# Message”当作输入有效。某些 transfer-encoding 问题只在解码 payload 时发现。strict policy 把
# handle_defect 改为直接抛对应 MessageDefect，适合拒绝式入口，但会失去宽容迁移能力。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.email.errors.MessageDefect
# polyglot-covers: python.email.message.defects
# polyglot-covers: python.email.policy.handle_defect
# polyglot-covers: python.email.policy.register_defect
# polyglot-covers: python.email.errors.NoBoundaryInMultipartDefect
# polyglot-covers: python.email.errors.MultipartInvariantViolationDefect
# polyglot-covers: python.email.errors.CloseBoundaryNotFoundDefect
# polyglot-covers: python.email.errors.MissingHeaderBodySeparatorDefect
# polyglot-covers: python.email.errors.InvalidBase64CharactersDefect
# polyglot-covers: python.email.base64-defect-discovered-on-decode
# polyglot-covers: python.email.policy-raise-on-defect
# polyglot-covers: python.email.parser-recovery-does-not-mean-valid
# polyglot-covers: python.email.errors.MessageError
# polyglot-covers: python.email.errors.MessageParseError
# polyglot-covers: python.email.errors.HeaderParseError
# polyglot-covers: python.email.errors.BoundaryError
# polyglot-covers: python.email.errors.MultipartConversionError
# polyglot-covers: python.email.errors.HeaderWriteError-3.10.15




def defect_types(message):
    return {type(defect) for defect in message.defects}


def test_missing_boundary_is_recorded_and_strict_policy_raises_first_defect():
    raw = b"Content-Type: multipart/mixed\r\n\r\nbody\r\n"
    recovered = BytesParser(policy=policy.default).parsebytes(raw)
    assert errors.NoBoundaryInMultipartDefect in defect_types(recovered)
    assert errors.MultipartInvariantViolationDefect in defect_types(recovered)
    assert recovered.get_content_type() == "multipart/mixed"
    assert recovered.is_multipart() is False

    strict = policy.default.clone(raise_on_defect=True)
    with pytest.raises(errors.NoBoundaryInMultipartDefect):
        BytesParser(policy=strict).parsebytes(raw)


def test_unclosed_boundary_and_missing_header_separator_have_specific_defects():
    unclosed = (
        b"Content-Type: multipart/mixed; boundary=x\r\n\r\n"
        b"--x\r\nContent-Type: text/plain\r\n\r\npart\r\n"
    )
    parsed = BytesParser(policy=policy.default).parsebytes(unclosed)
    assert errors.CloseBoundaryNotFoundDefect in defect_types(parsed)

    malformed = b"Subject: ok\r\nthis line starts the body\r\nbody\r\n"
    parsed = BytesParser(policy=policy.default).parsebytes(malformed)
    assert errors.MissingHeaderBodySeparatorDefect in defect_types(parsed)
    assert parsed.get_payload().startswith("this line starts the body")


def test_invalid_base64_characters_are_registered_when_payload_is_decoded():
    raw = (
        b"Content-Type: application/octet-stream\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\n"
        b"YWJj!!\r\n"
    )
    parsed = BytesParser(policy=policy.default).parsebytes(raw)
    assert parsed.defects == []
    assert parsed.get_content() == b"abc"
    assert errors.InvalidBase64CharactersDefect in defect_types(parsed)


def test_email_error_hierarchy_separates_parse_and_structure_failures():
    assert issubclass(errors.MessageParseError, errors.MessageError)
    assert issubclass(errors.HeaderParseError, errors.MessageParseError)
    assert issubclass(errors.BoundaryError, errors.MessageParseError)
    assert issubclass(errors.MultipartConversionError, errors.MessageError)
    if hasattr(errors, "HeaderWriteError"):
        assert issubclass(errors.HeaderWriteError, errors.MessageError)


# headerregistry 的 Address/Group、结构化 address header 与 DateHeader。
#
# policy.default 返回 str 子类 header，不必手拆引号、逗号和 encoded-word。Address 保存无引号的
# display_name/username/domain，并生成合法 addr_spec；Group 保留收件人组边界，而 ``addresses``
# 提供扁平视图。Date header 接受 aware datetime 并能无损取回时区信息。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.email.headerregistry.BaseHeader
# polyglot-covers: python.email.headerregistry.Address
# polyglot-covers: python.email.headerregistry.Address.display_name
# polyglot-covers: python.email.headerregistry.Address.username
# polyglot-covers: python.email.headerregistry.Address.domain
# polyglot-covers: python.email.headerregistry.Address.addr_spec
# polyglot-covers: python.email.headerregistry.Group
# polyglot-covers: python.email.headerregistry.AddressHeader.addresses
# polyglot-covers: python.email.headerregistry.AddressHeader.groups
# polyglot-covers: python.email.headerregistry.SingleAddressHeader.address
# polyglot-covers: python.email.headerregistry.DateHeader.datetime
# polyglot-covers: python.email.structured-header-defects
# polyglot-covers: python.email.invalid-addr-spec-header-parse-error
# polyglot-covers: python.email.headerregistry.Address.__str__
# polyglot-covers: python.email.headerregistry.Group.display_name
# polyglot-covers: python.email.headerregistry.Group.addresses
# polyglot-covers: python.email.headerregistry.Group.__str__




def test_address_headers_preserve_groups_and_offer_a_flat_address_view():
    sender = Address(display_name="发送者", username="sender", domain="example.test")
    direct = Address(addr_spec='"quoted local"@example.test')
    team_member = Address(display_name="Member", username="member", domain="example.test")
    team = Group(display_name="Team", addresses=(team_member,))

    message = EmailMessage()
    message["From"] = sender
    message["Sender"] = sender
    message["To"] = (direct, team)
    from_header = message["From"]
    to_header = message["To"]

    assert isinstance(from_header, BaseHeader)
    # From 是可含多个地址的 AddressHeader，即使当前只有一个也通过 addresses 暴露；
    # Sender 才是 SingleAddressHeader，提供便捷的 address 属性。
    assert from_header.addresses == (sender,)
    sender_address = message["Sender"].address
    assert sender_address.display_name == "发送者"
    assert sender_address.username == "sender"
    assert sender_address.domain == "example.test"
    assert direct.addr_spec == '"quoted local"@example.test'
    assert str(team_member) == "Member <member@example.test>"
    assert team.display_name == "Team"
    assert team.addresses == (team_member,)
    assert str(team) == "Team: Member <member@example.test>;"
    assert to_header.addresses == (direct, team_member)
    # 解析器会构造新的 Group 值对象；比起依赖对象相等的实现细节，直接检查结构更能说明协议。
    assert to_header.groups[1].display_name == "Team"
    assert to_header.groups[1].addresses == (team_member,)
    assert to_header.defects == ()


def test_date_header_keeps_an_aware_datetime_value():
    instant = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=8)))
    message = EmailMessage()
    message["Date"] = instant
    assert message["Date"].datetime == instant
    assert "+0800" in str(message["Date"])


def test_address_rejects_an_addr_spec_that_cannot_be_fully_parsed():
    with pytest.raises(errors.HeaderParseError):
        Address(addr_spec="bad@@example.test")


# 结构化 MIME header 与 HeaderRegistry 类型映射扩展。
#
# Content-Type/Disposition/Transfer-Encoding/MIME-Version 在现代 policy 下具有专门属性，不应靠
# split(';') 解析带引号参数。HeaderRegistry 按字段名选择 mixin；未知字段使用 UnstructuredHeader，
# map_to_type 可为私有字段注册语义类。Unique mixin 的 max_count=1 会参与程序化赋值校验。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.email.headerregistry.ContentTypeHeader
# polyglot-covers: python.email.headerregistry.ContentDispositionHeader
# polyglot-covers: python.email.headerregistry.ContentTransferEncodingHeader
# polyglot-covers: python.email.headerregistry.MIMEVersionHeader
# polyglot-covers: python.email.mime-header-params
# polyglot-covers: python.email.headerregistry.HeaderRegistry
# polyglot-covers: python.email.headerregistry.HeaderRegistry.__getitem__
# polyglot-covers: python.email.headerregistry.HeaderRegistry.__call__
# polyglot-covers: python.email.headerregistry.HeaderRegistry.map_to_type
# polyglot-covers: python.email.headerregistry.UnstructuredHeader
# polyglot-covers: python.email.headerregistry.UniqueUnstructuredHeader
# polyglot-covers: python.email.headerregistry.header-max-count
# polyglot-covers: python.email.headerregistry.BaseHeader.name
# polyglot-covers: python.email.headerregistry.BaseHeader.defects
# polyglot-covers: python.email.headerregistry.BaseHeader.fold
# polyglot-covers: python.email.headerregistry.MIMEVersionHeader.major
# polyglot-covers: python.email.headerregistry.MIMEVersionHeader.minor



def test_mime_headers_expose_normalized_values_and_parameter_mappings():
    message = EmailMessage()
    message["Content-Type"] = "Text/Plain; Charset=UTF-8; format=flowed"
    message["Content-Disposition"] = 'attachment; filename="report.txt"'
    message["Content-Transfer-Encoding"] = "BASE64"
    message["MIME-Version"] = "1.0"

    content_type = message["Content-Type"]
    assert content_type.content_type == "text/plain"
    assert content_type.maintype == "text"
    assert content_type.subtype == "plain"
    assert content_type.params["charset"].lower() == "utf-8"
    assert content_type.params["format"] == "flowed"
    assert message["Content-Disposition"].content_disposition == "attachment"
    assert message["Content-Disposition"].params["filename"] == "report.txt"
    assert message["Content-Transfer-Encoding"].cte == "base64"
    assert message["MIME-Version"].version == "1.0"
    assert message["MIME-Version"].major == 1
    assert message["MIME-Version"].minor == 0


def test_header_registry_selects_default_and_custom_unique_header_mixins():
    registry = HeaderRegistry()
    subject_class = registry["Subject"]
    assert subject_class.max_count == 1

    ordinary = registry("X-Free", "value")
    assert isinstance(ordinary, BaseHeader)
    assert ordinary.name == "X-Free"
    assert ordinary.max_count is None
    assert ordinary.defects == ()
    assert ordinary.fold(policy=policy.default) == "X-Free: value\n"

    registry.map_to_type("X-Once", UniqueUnstructuredHeader)
    unique = registry("X-Once", "one")
    assert isinstance(unique, BaseHeader)
    assert unique.name == "X-Once"
    assert unique.max_count == 1
