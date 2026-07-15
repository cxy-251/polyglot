"""424｜Maildir 与 mbox/MMDF 之间的格式状态转换表。

格式消息构造器不只复制 headers/body，还尽可能转换状态：Maildir S/F/R/T 对应单文件格式的
R/F/A/D，cur 对应 O。反向转换时 Status/X-Status 被消费并从普通 headers 移除；mbox 与
MMDF 的 From 行和五种 flags 则可直接互转。不了解这一步会造成“复制后状态 header 消失”的误判。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.format-state-conversion
# polyglot-covers: python.mailbox.MaildirMessage-from-mboxMessage
# polyglot-covers: python.mailbox.MaildirMessage-from-MMDFMessage
# polyglot-covers: python.mailbox.Maildir-conversion-omits-status-headers
# polyglot-covers: python.mailbox.mboxMessage-from-MaildirMessage
# polyglot-covers: python.mailbox.MMDFMessage-from-MaildirMessage
# polyglot-covers: python.mailbox.maildir-s-to-mbox-r
# polyglot-covers: python.mailbox.maildir-cur-to-mbox-o
# polyglot-covers: python.mailbox.maildir-t-f-r-to-mbox-d-f-a
# polyglot-covers: python.mailbox.mbox-and-mmdf-direct-state-conversion
# polyglot-covers: python.mailbox.maildir-date-generates-from-line

import mailbox


def test_maildir_state_converts_to_mbox_and_mmdf_flags_and_envelope_line():
    source = mailbox.MaildirMessage("Subject: converted\n\nbody\n")
    source.set_subdir("cur")
    source.set_flags("FRST")
    source.set_date(1_000_000_000.0)

    mbox_message = mailbox.mboxMessage(source)
    mmdf_message = mailbox.MMDFMessage(source)
    assert set(mbox_message.get_flags()) == set("RODFA")
    assert set(mmdf_message.get_flags()) == set("RODFA")
    assert mbox_message.get_from()
    assert mmdf_message.get_from()


def test_mbox_and_mmdf_state_converts_back_to_maildir_without_status_headers():
    source = mailbox.mboxMessage("Subject: source\n\nbody\n")
    source.set_from("sender@example.test Sat Jan  1 00:00:00 2000")
    source.set_flags("RODFA")

    maildir_message = mailbox.MaildirMessage(source)
    assert maildir_message.get_subdir() == "cur"
    assert set(maildir_message.get_flags()) == set("FRST")
    assert maildir_message["Status"] is None
    assert maildir_message["X-Status"] is None

    mmdf_message = mailbox.MMDFMessage(source)
    assert mmdf_message.get_from() == source.get_from()
    assert set(mmdf_message.get_flags()) == set(source.get_flags())
    round_trip = mailbox.MaildirMessage(mmdf_message)
    assert set(round_trip.get_flags()) == set("FRST")
