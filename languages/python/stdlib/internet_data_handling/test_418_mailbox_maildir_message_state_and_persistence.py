"""418｜MaildirMessage 的 new/cur、info、flags、delivery date 与落盘状态。

Maildir 把是否已被邮箱看到（cur/new）与是否已读（S flag）分开。标准 info 形如 ``2,FS``，
flags 按字母排序；实验性 info 不解释为 flags，add_flag 会把它覆盖成标准 ``2,`` 格式。
delivery date 最终由消息文件 mtime 表示，因此比较时要考虑文件系统时间精度。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.MaildirMessage
# polyglot-covers: python.mailbox.MaildirMessage.get_subdir
# polyglot-covers: python.mailbox.MaildirMessage.set_subdir
# polyglot-covers: python.mailbox.MaildirMessage-invalid-subdir
# polyglot-covers: python.mailbox.MaildirMessage.get_info
# polyglot-covers: python.mailbox.MaildirMessage.set_info
# polyglot-covers: python.mailbox.MaildirMessage.get_flags
# polyglot-covers: python.mailbox.MaildirMessage.set_flags
# polyglot-covers: python.mailbox.MaildirMessage.add_flag
# polyglot-covers: python.mailbox.MaildirMessage.remove_flag
# polyglot-covers: python.mailbox.MaildirMessage-flags-sorted
# polyglot-covers: python.mailbox.MaildirMessage-experimental-info
# polyglot-covers: python.mailbox.MaildirMessage.get_date
# polyglot-covers: python.mailbox.MaildirMessage.set_date
# polyglot-covers: python.mailbox.Maildir-format-state-persistence
# polyglot-covers: python.mailbox.maildir-cur-is-not-read-flag

import mailbox

import pytest


def test_maildir_state_methods_keep_subdirectory_flags_info_and_fixed_date():
    message = mailbox.MaildirMessage("Subject: state\n\nbody\n")
    message.set_subdir("cur")
    message.set_flags("SRF")
    message.set_date(1_000_000_000.0)

    assert message.get_subdir() == "cur"
    assert message.get_flags() == "FRS"
    assert message.get_info() == "2,FRS"
    assert message.get_date() == 1_000_000_000.0
    with pytest.raises(ValueError):
        message.set_subdir("seen")


def test_experimental_info_is_not_flags_and_add_flag_replaces_it():
    message = mailbox.MaildirMessage()
    message.set_info("1,vendor-data")

    assert message.get_flags() == ""
    message.remove_flag("S")
    assert message.get_info() == "1,vendor-data"
    message.add_flag("SF")
    assert message.get_info() == "2,FS"
    message.remove_flag("F")
    assert message.get_flags() == "S"


def test_maildir_persists_format_state_in_filename_and_file_metadata(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    message = mailbox.MaildirMessage("Subject: persisted\n\nbody\n")
    message.set_subdir("cur")
    message.set_flags("FS")
    message.set_date(1_000_000_000.0)
    key = box.add(message)

    stored = box.get_message(key)
    assert stored.get_subdir() == "cur"
    assert stored.get_flags() == "FS"
    assert stored.get_date() == pytest.approx(1_000_000_000.0, abs=1.0)
    # cur 只表示消息已被邮箱程序发现；真正的“已读”状态仍由独立的 S flag 表示。
    stored.remove_flag("S")
    assert stored.get_subdir() == "cur"
    assert "S" not in stored.get_flags()
