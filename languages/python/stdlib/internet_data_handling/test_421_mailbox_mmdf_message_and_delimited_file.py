"""421｜MMDFMessage 状态与 Control-A 分隔的单文件邮箱。

MMDFMessage 与 mboxMessage 共享 envelope From 和 R/O/D/F/A flags，MMDF 另用四个 Control-A
字符组成的行分隔消息。CPython 3.10 的 MMDF 与 mbox 共用 writer，仍会把正文 ``From `` 写成
``>From ``；读取这种原始格式时不能假定只因有 Control-A 分隔就不会出现 mbox 风格转义。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.MMDF
# polyglot-covers: python.mailbox.MMDFMessage
# polyglot-covers: python.mailbox.MMDFMessage.get_from
# polyglot-covers: python.mailbox.MMDFMessage.set_from
# polyglot-covers: python.mailbox.MMDFMessage.get_flags
# polyglot-covers: python.mailbox.MMDFMessage.set_flags
# polyglot-covers: python.mailbox.MMDFMessage.add_flag
# polyglot-covers: python.mailbox.MMDFMessage.remove_flag
# polyglot-covers: python.mailbox.MMDF-control-a-delimiter
# polyglot-covers: python.mailbox.MMDF-shared-from-body-mangling
# polyglot-covers: python.mailbox.MMDF.lock
# polyglot-covers: python.mailbox.MMDF.unlock
# polyglot-covers: python.mailbox.MMDF.flush
# polyglot-covers: python.mailbox.MMDF.close
# polyglot-covers: python.mailbox.MMDF.get_file-lifetime

import mailbox


FROM_LINE = "sender@example.test Sat Jan  1 00:00:00 2000"


def test_mmdf_message_uses_the_same_envelope_and_flag_model_as_mbox():
    message = mailbox.MMDFMessage("Subject: state\n\nbody\n")
    message.set_from(FROM_LINE)
    message.set_flags("RODFA")
    message.remove_flag("OD")
    message.add_flag("OD")

    assert message.get_from() == FROM_LINE
    assert set(message.get_flags()) == set("RODFA")
    assert set(message["Status"]) == set("RO")
    assert set(message["X-Status"]) == set("DFA")


def test_mmdf_file_workflow_persists_control_a_delimiters_and_format_state(tmp_path):
    path = tmp_path / "messages.mmdf"
    box = mailbox.MMDF(path)
    message = mailbox.MMDFMessage(
        "Subject: delimited\n\nbefore\nFrom remains ordinary body text\nafter\n"
    )
    message.set_from(FROM_LINE)
    message.set_flags("RF")

    box.lock()
    try:
        key = box.add(message)
        box.flush()
    finally:
        box.unlock()

    raw = path.read_bytes()
    assert raw.startswith(b"\x01\x01\x01\x01\n")
    assert b"\n>From remains ordinary body text\n" in raw
    stored = box.get_message(key)
    assert stored.get_from() == FROM_LINE
    assert stored.get_flags() == "RF"
    with box.get_file(key) as view:
        assert b"Subject: delimited" in view.read()
    box.close()

    reopened = mailbox.MMDF(path, create=False)
    assert reopened[key]["Subject"] == "delimited"
    reopened.close()
