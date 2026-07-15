"""398｜宽容 parser 的 defects、延迟 Base64 defect 与 raise_on_defect。

Feed parser 尽力保留不合规邮件，并把问题登记在实际出错 part 的 defects；调用者不能把“成功返回
Message”当作输入有效。某些 transfer-encoding 问题只在解码 payload 时发现。strict policy 把
handle_defect 改为直接抛对应 MessageDefect，适合拒绝式入口，但会失去宽容迁移能力。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from email import errors, policy
from email.parser import BytesParser

import pytest


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
