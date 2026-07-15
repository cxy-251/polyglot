"""396｜BytesGenerator/Generator 的 stream 类型、From_ mangling 与 clone。

BytesGenerator 写 binary stream，Generator 写 text stream；前者能保留 8-bit 数据，通常更适合
邮件。mangle_from_=True 只转义正文行首精确的 ``From ``，供 mbox 使用。flatten 可覆盖 unixfrom
和 linesep；clone 保留所有生成选项但换用独立 output stream，适合递归/并行目标。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from email import policy
from email.generator import BytesGenerator, Generator
from email.message import EmailMessage
import io


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
