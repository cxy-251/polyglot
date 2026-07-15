"""426｜mailbox.Message 输入复制，以及 NoSuch/NotEmpty/Clash/Format 异常。

mailbox.Message 可从 email Message、str、bytes、二进制文件对象构造，且从 Message 构造是内容
复制而不是共享 headers。mailbox 专用异常区分路径不存在、目录非空、外部锁冲突和格式损坏；
处理邮件正文解析错误时不要误把这些存储层异常都吞成同一种失败。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.Message
# polyglot-covers: python.mailbox.Message-from-email-message
# polyglot-covers: python.mailbox.Message-copy-not-alias
# polyglot-covers: python.mailbox.Message-from-string
# polyglot-covers: python.mailbox.Message-from-bytes
# polyglot-covers: python.mailbox.Message-from-binary-file
# polyglot-covers: python.mailbox.Error
# polyglot-covers: python.mailbox.NoSuchMailboxError
# polyglot-covers: python.mailbox.NotEmptyError
# polyglot-covers: python.mailbox.ExternalClashError
# polyglot-covers: python.mailbox.FormatError
# polyglot-covers: python.mailbox.create-false-missing-mailbox
# polyglot-covers: python.mailbox.single-file-lock-contention
# polyglot-covers: python.mailbox.mh-corrupt-sequences-format-error

from email.message import Message
from io import BytesIO
import mailbox

import pytest


WIRE = "Subject: constructed\n\nbody\n"


def test_mailbox_message_constructs_from_supported_sources_and_copies_message_state():
    source = Message()
    source["Subject"] = "original"
    source.set_payload("body")
    copied = mailbox.Message(source)
    source.replace_header("Subject", "mutated")

    assert copied["Subject"] == "original"
    assert mailbox.Message(WIRE)["Subject"] == "constructed"
    assert mailbox.Message(WIRE.encode())["Subject"] == "constructed"
    assert mailbox.Message(BytesIO(WIRE.encode()))["Subject"] == "constructed"


def test_mailbox_exception_types_share_error_base_and_missing_path_raises(tmp_path):
    for exception_type in (
        mailbox.NoSuchMailboxError,
        mailbox.NotEmptyError,
        mailbox.ExternalClashError,
        mailbox.FormatError,
    ):
        assert issubclass(exception_type, mailbox.Error)

    with pytest.raises(mailbox.NoSuchMailboxError):
        mailbox.Maildir(tmp_path / "absent", create=False)


def test_two_single_file_handles_report_advisory_lock_contention(tmp_path):
    path = tmp_path / "locked.mbox"
    first = mailbox.mbox(path)
    second = mailbox.mbox(path)
    first.lock()
    try:
        with pytest.raises(mailbox.ExternalClashError):
            second.lock()
    finally:
        first.unlock()
        second.close()
        first.close()


def test_mh_rejects_a_malformed_sequences_file_as_format_error(tmp_path):
    path = tmp_path / "mh"
    box = mailbox.MH(path)
    (path / ".mh_sequences").write_text("missing colon\n", encoding="ascii")

    with pytest.raises(mailbox.FormatError):
        box.get_sequences()
