"""394｜BytesParser/Parser、top-level convenience 与 header-only 快路径。

完整消息优先用 binary parser，并显式传 policy.default，才能得到 EmailMessage 与结构化 header；
不传 policy 在 3.10 仍默认为 compat32/Message，未来会改变。HeaderParser 只解析 header，把整个 MIME
body 留作原始 payload，适合只做路由信息但不能据此判断真实 multipart 子树。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
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


SIMPLE_BYTES = b"From: sender@example.test\r\nSubject: hello\r\n\r\nbody\r\n"


def test_binary_and_text_parsers_accept_whole_values_or_file_objects():
    byte_parser = BytesParser(policy=policy.default)
    from_bytes = byte_parser.parsebytes(memoryview(SIMPLE_BYTES))
    from_binary_file = byte_parser.parse(io.BytesIO(SIMPLE_BYTES))
    assert isinstance(from_bytes, EmailMessage)
    assert from_bytes.get_content() == "body\r\n"
    assert from_binary_file.as_bytes() == from_bytes.as_bytes()

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
