"""420｜mboxMessage 的 envelope From、flags，以及单文件邮箱的锁与转义。

mbox 用 ``From `` 行分隔消息，因此正文行若也以 ``From `` 开头，生成器会写成 ``>From ``；
这是格式要求，不是正文业务转义。状态 flags 分布在 Status/X-Status headers。单文件邮箱修改前
应 lock，flush 才保证待处理替换写回磁盘，get_file 视图不能跨 flush/close 长期保存。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.mbox
# polyglot-covers: python.mailbox.mboxMessage
# polyglot-covers: python.mailbox.mboxMessage.get_from
# polyglot-covers: python.mailbox.mboxMessage.set_from
# polyglot-covers: python.mailbox.mboxMessage.set-from-fixed-time-tuple
# polyglot-covers: python.mailbox.mboxMessage.get_flags
# polyglot-covers: python.mailbox.mboxMessage.set_flags
# polyglot-covers: python.mailbox.mboxMessage.add_flag
# polyglot-covers: python.mailbox.mboxMessage.remove_flag
# polyglot-covers: python.mailbox.mbox-status-x-status-flags
# polyglot-covers: python.mailbox.mbox-from-line-delimiter
# polyglot-covers: python.mailbox.mbox-from-body-mangling
# polyglot-covers: python.mailbox.mbox.lock
# polyglot-covers: python.mailbox.mbox.unlock
# polyglot-covers: python.mailbox.mbox.flush
# polyglot-covers: python.mailbox.mbox.close
# polyglot-covers: python.mailbox.mbox.get_file-lifetime
# polyglot-covers: python.mailbox.Mailbox.lock
# polyglot-covers: python.mailbox.Mailbox.unlock
# polyglot-covers: python.mailbox.Mailbox.flush
# polyglot-covers: python.mailbox.Mailbox.close

import mailbox
import time


FROM_LINE = "sender@example.test Sat Jan  1 00:00:00 2000"


def test_mbox_message_manages_envelope_line_and_conventional_flags():
    message = mailbox.mboxMessage("Subject: state\n\nbody\n")
    message.set_from(FROM_LINE)
    message.set_flags("RODFA")

    assert message.get_from() == FROM_LINE
    assert message.get_flags() == "RODFA"
    assert message["Status"] == "RO"
    assert message["X-Status"] == "DFA"
    message.remove_flag("OD")
    message.add_flag("OD")
    assert set(message.get_flags()) == set("RODFA")

    fixed = mailbox.mboxMessage()
    fixed.set_from("sender@example.test", time.gmtime(0))
    assert fixed.get_from() == "sender@example.test Thu Jan  1 00:00:00 1970"


def test_mbox_workflow_locks_flushes_and_mangles_body_from_lines(tmp_path):
    path = tmp_path / "messages.mbox"
    box = mailbox.mbox(path)
    message = mailbox.mboxMessage(
        "Subject: escaped\n\nbefore\nFrom body is not a delimiter\nafter\n"
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
    assert raw.startswith(f"From {FROM_LINE}\n".encode())
    assert b"\n>From body is not a delimiter\n" in raw
    stored = box.get_message(key)
    assert stored.get_from() == FROM_LINE
    assert stored.get_flags() == "RF"
    with box.get_file(key) as view:
        assert b"Subject: escaped" in view.read()
    box.close()

    reopened = mailbox.mbox(path, create=False)
    assert reopened[key]["Subject"] == "escaped"
    reopened.close()
