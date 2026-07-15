"""422｜MHMessage sequences、MH folder 与 pack 重新编号。

MH 每封消息是以数字命名的独立文件，状态由任意命名的 sequence 表示。Mailbox.set_sequences
一次重写 ``.mh_sequences``；pack 消除编号空洞并同步 sequence，但会让此前发出的旧 key 失效。
MH 删除立即发生，不采用传统的逗号前缀软删除；普通内容改动也即时落盘。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.MH
# polyglot-covers: python.mailbox.MHMessage
# polyglot-covers: python.mailbox.MHMessage.get_sequences
# polyglot-covers: python.mailbox.MHMessage.set_sequences
# polyglot-covers: python.mailbox.MHMessage.add_sequence
# polyglot-covers: python.mailbox.MHMessage.remove_sequence
# polyglot-covers: python.mailbox.MH.get_sequences
# polyglot-covers: python.mailbox.MH.set_sequences
# polyglot-covers: python.mailbox.MH.pack
# polyglot-covers: python.mailbox.MH-pack-invalidates-old-keys
# polyglot-covers: python.mailbox.MH-pack-updates-sequences
# polyglot-covers: python.mailbox.MH-remove-immediate
# polyglot-covers: python.mailbox.MH.remove
# polyglot-covers: python.mailbox.MH.__delitem__
# polyglot-covers: python.mailbox.MH.discard
# polyglot-covers: python.mailbox.MH.list_folders
# polyglot-covers: python.mailbox.MH.get_folder
# polyglot-covers: python.mailbox.MH.add_folder
# polyglot-covers: python.mailbox.MH.remove_folder
# polyglot-covers: python.mailbox.MH.lock
# polyglot-covers: python.mailbox.MH.unlock
# polyglot-covers: python.mailbox.MH.get_file
# polyglot-covers: python.mailbox.MH.flush-noop
# polyglot-covers: python.mailbox.MH.close-noop

import mailbox

import pytest


def test_mh_message_manages_arbitrary_named_sequences_without_duplicates():
    message = mailbox.MHMessage("Subject: state\n\nbody\n")
    message.set_sequences(["unseen", "project"])
    message.add_sequence("replied")
    message.add_sequence("project")
    message.remove_sequence("unseen")

    assert message.get_sequences() == ["project", "replied"]


def test_mh_pack_closes_numbering_gaps_updates_sequences_and_invalidates_old_key(tmp_path):
    box = mailbox.MH(tmp_path / "mh")
    keys = [
        box.add("Subject: one\n\nbody\n"),
        box.add("Subject: two\n\nbody\n"),
        box.add("Subject: three\n\nbody\n"),
    ]
    box.set_sequences({"unseen": [keys[0], keys[2]], "flagged": [keys[2]]})
    box.remove(keys[1])

    box.lock()
    try:
        box.pack()
    finally:
        box.unlock()

    assert box.keys() == [1, 2]
    assert box.get_sequences() == {"unseen": [1, 2], "flagged": [2]}
    with pytest.raises(KeyError):
        box.get_message(keys[2])
    with box.get_file(2) as stream:
        assert b"Subject: three" in stream.read()


def test_mh_folders_are_nested_mh_mailboxes_and_lifecycle_writes_immediately(tmp_path):
    root = mailbox.MH(tmp_path / "mh")
    child = root.add_folder("child")
    child.add("Subject: nested\n\nbody\n")

    assert root.list_folders() == ["child"]
    assert isinstance(root.get_folder("child"), mailbox.MH)
    with pytest.raises(mailbox.NotEmptyError):
        root.remove_folder("child")
    child.clear()
    root.remove_folder("child")
    root.flush()
    root.close()


def test_mh_remove_del_and_discard_all_delete_message_files_immediately(tmp_path):
    box = mailbox.MH(tmp_path / "mh")
    remove_key = box.add("Subject: remove\n\nbody\n")
    del_key = box.add("Subject: del\n\nbody\n")
    discard_key = box.add("Subject: discard\n\nbody\n")

    box.remove(remove_key)
    del box[del_key]
    box.discard(discard_key)
    box.discard(discard_key)
    assert len(box) == 0
