"""419｜Maildir folder、过期 tmp 清理，以及无锁即时写入生命周期。

Maildir folder 以独立 Maildir 表示；非空 folder 不能删除。clean 只移除超过 36 小时的 tmp
文件，本例用固定旧时间戳而不 sleep。Maildir 每次变更立即落盘，不保持打开文件，也不需要
邮箱级锁，所以 flush/lock/unlock/close 都是兼容通用接口的 no-op。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.Maildir
# polyglot-covers: python.mailbox.Maildir-create-layout
# polyglot-covers: python.mailbox.Maildir.list_folders
# polyglot-covers: python.mailbox.Maildir.get_folder
# polyglot-covers: python.mailbox.Maildir.add_folder
# polyglot-covers: python.mailbox.Maildir.remove_folder
# polyglot-covers: python.mailbox.Maildir-folder-not-empty
# polyglot-covers: python.mailbox.Maildir-folder-missing
# polyglot-covers: python.mailbox.Maildir.clean
# polyglot-covers: python.mailbox.Maildir-clean-36-hour-threshold
# polyglot-covers: python.mailbox.Maildir.colon
# polyglot-covers: python.mailbox.Maildir-instance-colon-portability
# polyglot-covers: python.mailbox.Maildir.flush-noop
# polyglot-covers: python.mailbox.Maildir.lock-noop
# polyglot-covers: python.mailbox.Maildir.unlock-noop
# polyglot-covers: python.mailbox.Maildir.close-noop

import os
import mailbox

import pytest


def test_folder_workflow_rejects_missing_and_nonempty_removal(tmp_path):
    root = mailbox.Maildir(tmp_path / "maildir")
    archive = root.add_folder("Archive")

    assert root.list_folders() == ["Archive"]
    assert isinstance(root.get_folder("Archive"), mailbox.Maildir)
    archive.add("Subject: saved\n\nbody\n")
    with pytest.raises(mailbox.NotEmptyError):
        root.remove_folder("Archive")

    archive.clear()
    root.remove_folder("Archive")
    assert root.list_folders() == []
    with pytest.raises(mailbox.NoSuchMailboxError):
        root.get_folder("missing")


def test_clean_deletes_only_old_temporary_files_without_waiting(tmp_path):
    path = tmp_path / "maildir"
    box = mailbox.Maildir(path)
    stale = path / "tmp" / "stale"
    fresh = path / "tmp" / "fresh"
    stale.write_bytes(b"old")
    fresh.write_bytes(b"new")
    os.utime(stale, (0, 0))

    box.clean()
    assert not stale.exists()
    assert fresh.exists()


def test_maildir_lifecycle_methods_are_safe_noops_because_writes_are_immediate(tmp_path):
    path = tmp_path / "maildir"
    box = mailbox.Maildir(path)
    key = box.add("Subject: immediate\n\nbody\n")
    box.lock()
    box.flush()
    box.unlock()
    box.close()

    reopened = mailbox.Maildir(path, create=False)
    assert reopened[key]["Subject"] == "immediate"


def test_maildir_colon_separator_can_be_overridden_per_instance(tmp_path):
    path = tmp_path / "portable-maildir"
    box = mailbox.Maildir(path)
    box.colon = "!"
    message = mailbox.MaildirMessage("Subject: portable\n\nbody\n")
    message.set_subdir("cur")
    message.set_flags("S")

    box.add(message)
    names = [entry.name for entry in (path / "cur").iterdir()]
    assert len(names) == 1
    assert "!2,S" in names[0]
