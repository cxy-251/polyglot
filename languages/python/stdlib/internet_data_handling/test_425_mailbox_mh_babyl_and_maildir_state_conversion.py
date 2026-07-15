"""425｜MH sequence、Babyl label 与 Maildir/mbox flags 的状态转换。

unseen、replied、flagged 等概念在不同格式里分别是 sequence、label 或 flag。构造目标格式消息时，
标准库只转换有公认对应关系的状态：例如 Maildir 无 S 变 MH/Babyl unseen，P 只在 Babyl 中成为
forwarded。自定义 sequence/label 没有通用映射，会在跨格式转换中丢失。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.MHMessage-from-MaildirMessage
# polyglot-covers: python.mailbox.BabylMessage-from-MaildirMessage
# polyglot-covers: python.mailbox.maildir-to-mh-unseen-replied-flagged
# polyglot-covers: python.mailbox.maildir-to-babyl-state-labels
# polyglot-covers: python.mailbox.MaildirMessage-from-MHMessage
# polyglot-covers: python.mailbox.mboxMessage-from-MHMessage
# polyglot-covers: python.mailbox.BabylMessage-from-MHMessage
# polyglot-covers: python.mailbox.mh-to-maildir-state
# polyglot-covers: python.mailbox.mh-to-mbox-state
# polyglot-covers: python.mailbox.mh-to-babyl-state
# polyglot-covers: python.mailbox.custom-format-state-not-portable

import mailbox


def test_maildir_flags_convert_to_standard_mh_sequences_and_babyl_labels():
    source = mailbox.MaildirMessage("Subject: source\n\nbody\n")
    source.set_subdir("cur")
    source.set_flags("FPRT")

    mh_message = mailbox.MHMessage(source)
    babyl_message = mailbox.BabylMessage(source)
    assert set(mh_message.get_sequences()) == {"unseen", "replied", "flagged"}
    assert set(babyl_message.get_labels()) == {
        "unseen",
        "deleted",
        "answered",
        "forwarded",
    }


def test_mh_sequences_convert_to_maildir_mbox_and_babyl_standard_state_only():
    source = mailbox.MHMessage("Subject: source\n\nbody\n")
    source.set_sequences(["unseen", "replied", "flagged", "project-custom"])

    maildir_message = mailbox.MaildirMessage(source)
    mbox_message = mailbox.mboxMessage(source)
    babyl_message = mailbox.BabylMessage(source)

    assert maildir_message.get_subdir() == "cur"
    assert set(maildir_message.get_flags()) == set("FR")
    assert set(mbox_message.get_flags()) == set("OFA")
    assert set(babyl_message.get_labels()) == {"unseen", "answered"}
    assert "project-custom" not in babyl_message.get_labels()
