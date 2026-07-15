"""397｜非变换 policy 的 bytes roundtrip 与 DecodedGenerator 人类视图。

BytesParser + BytesGenerator 在相同、非变换 policy 下以字节往返为目标；默认 refold_source=long
可能重折长 header，所以需要原样签名/归档时应显式选择 refold_source=none。DecodedGenerator 不
生成可发送 MIME：它解码 text，并用模板占位非文本 part，适合日志或终端摘要。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.bytes-parser-generator-roundtrip
# polyglot-covers: python.email.policy.refold_source
# polyglot-covers: python.email.nontransforming-policy-workflow
# polyglot-covers: python.email.generator.DecodedGenerator
# polyglot-covers: python.email.decoded-generator-text-decoded
# polyglot-covers: python.email.decoded-generator-nontext-template
# polyglot-covers: python.email.decoded-generator-not-wire-format

from email import policy
from email.generator import BytesGenerator, DecodedGenerator
from email.message import EmailMessage
from email.parser import BytesParser
import io


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
