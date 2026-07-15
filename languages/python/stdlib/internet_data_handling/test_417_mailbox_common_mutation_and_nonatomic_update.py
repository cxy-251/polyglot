"""417｜Mailbox 的替换、删除、update、pop 与 clear 语义。

__setitem__ 只能替换既有 key；对普通替换消息，原有格式状态应保留。remove/del 缺 key 抛错，
discard 则适合面对并发删除。update 也不能创建新 key，且失败前已完成的替换不会回滚，因此它
不是事务。pop/popitem/clear 与映射类似，但返回值仍经过邮箱 factory。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.Mailbox.__setitem__
# polyglot-covers: python.mailbox.replace-preserves-format-state
# polyglot-covers: python.mailbox.Mailbox.__contains__
# polyglot-covers: python.mailbox.Mailbox.__len__
# polyglot-covers: python.mailbox.Mailbox.remove
# polyglot-covers: python.mailbox.Mailbox.__delitem__
# polyglot-covers: python.mailbox.Mailbox.discard
# polyglot-covers: python.mailbox.remove-missing-keyerror
# polyglot-covers: python.mailbox.discard-missing-no-error
# polyglot-covers: python.mailbox.Mailbox.update
# polyglot-covers: python.mailbox.update-existing-keys-only
# polyglot-covers: python.mailbox.update-partial-change-not-rolled-back
# polyglot-covers: python.mailbox.Mailbox.pop
# polyglot-covers: python.mailbox.Mailbox.popitem
# polyglot-covers: python.mailbox.Mailbox.clear
# polyglot-covers: python.mailbox.Maildir.add
# polyglot-covers: python.mailbox.Maildir.__setitem__
# polyglot-covers: python.mailbox.Maildir.update
# polyglot-covers: python.mailbox.Maildir-pid-filename-thread-coordination-trap

import mailbox

import pytest


def message(subject):
    return f"Subject: {subject}\n\nbody\n"


def test_replacement_keeps_key_and_existing_maildir_state(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    original = mailbox.MaildirMessage(message("original"))
    original.set_subdir("cur")
    original.set_flags("S")
    key = box.add(original)

    box[key] = message("replacement")
    stored = box.get_message(key)
    assert key in box
    assert stored["Subject"] == "replacement"
    assert stored.get_subdir() == "cur"
    assert stored.get_flags() == "S"
    with pytest.raises(KeyError):
        box["missing"] = message("cannot create")


def test_remove_raises_for_missing_key_while_discard_is_idempotent(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    key = box.add(message("delete"))
    del box[key]
    assert key not in box
    marker = object()
    assert box.get(key, marker) is marker
    with pytest.raises(KeyError):
        box[key]

    with pytest.raises(KeyError):
        box.remove(key)
    box.discard(key)


def test_update_requires_existing_keys_and_is_not_rolled_back_on_late_failure(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    key = box.add(message("before"))

    with pytest.raises(KeyError):
        box.update(
            [
                (key, message("changed first")),
                ("missing", message("then fails")),
            ]
        )
    assert box[key]["Subject"] == "changed first"


def test_pop_popitem_and_clear_remove_entries_with_mapping_like_results(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    first = box.add(message("first"))
    box.add(message("second"))

    assert box.pop(first)["Subject"] == "first"
    marker = object()
    assert box.pop("missing", marker) is marker
    key, removed = box.popitem()
    assert key not in box
    assert removed["Subject"] == "second"
    with pytest.raises(KeyError):
        box.popitem()

    box.add(message("one"))
    box.add(message("two"))
    box.clear()
    assert len(box) == 0
