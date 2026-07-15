"""110｜Mailbox 通用映射接口、输入形态与消息表示。

Mailbox 像映射但 key 由邮箱分配；add 可接收 Message、str、bytes 或二进制文件对象。
迭代 Mailbox 得到的是消息而不是 key，这是与 dict 最容易混淆的差异。get_message/get_bytes/
get_string/get_file 则让调用方明确选择对象、线格式或二进制流表示。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mailbox.Mailbox
# polyglot-covers: python.mailbox.Mailbox.add
# polyglot-covers: python.mailbox.add-message-input
# polyglot-covers: python.mailbox.add-string-input
# polyglot-covers: python.mailbox.add-bytes-input
# polyglot-covers: python.mailbox.add-binary-file-input
# polyglot-covers: python.mailbox.Mailbox.keys
# polyglot-covers: python.mailbox.Mailbox.iterkeys
# polyglot-covers: python.mailbox.Mailbox.values
# polyglot-covers: python.mailbox.Mailbox.itervalues
# polyglot-covers: python.mailbox.Mailbox.items
# polyglot-covers: python.mailbox.Mailbox.iteritems
# polyglot-covers: python.mailbox.Mailbox.__iter__
# polyglot-covers: python.mailbox.Mailbox.__iter__-yields-values
# polyglot-covers: python.mailbox.Mailbox.get
# polyglot-covers: python.mailbox.Mailbox.__getitem__
# polyglot-covers: python.mailbox.Mailbox.get_message
# polyglot-covers: python.mailbox.Mailbox.get_bytes
# polyglot-covers: python.mailbox.Mailbox.get_string
# polyglot-covers: python.mailbox.Mailbox.get_file
# polyglot-covers: python.mailbox.Mailbox-custom-factory
# polyglot-covers: python.mailbox.Maildir.get_file



from email.message import EmailMessage
from io import BytesIO
import mailbox
import pytest
import os
import time
from email.message import Message

def wire(subject):
    return f"Subject: {subject}\n\nbody for {subject}\n"


def test_add_accepts_supported_inputs_and_mapping_views_have_explicit_shapes(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    object_message = EmailMessage()
    object_message["Subject"] = "object"
    object_message.set_content("body")

    keys = [
        box.add(object_message),
        box.add(wire("string")),
        box.add(wire("bytes").encode()),
        box.add(BytesIO(wire("file").encode())),
    ]

    assert len(box) == 4
    assert set(box.keys()) == set(keys)
    assert set(box.iterkeys()) == set(keys)
    assert {message["Subject"] for message in box.values()} == {
        "object",
        "string",
        "bytes",
        "file",
    }
    assert len(list(box.itervalues())) == 4
    assert {key for key, _ in box.items()} == set(keys)
    assert {key for key, _ in box.iteritems()} == set(keys)
    # dict(box) 的直觉在这里会错：Mailbox.__iter__ 与 values()/itervalues() 同义。
    assert {message["Subject"] for message in box} == {
        "object",
        "string",
        "bytes",
        "file",
    }


def test_explicit_getters_return_message_bytes_string_or_binary_stream(tmp_path):
    box = mailbox.Maildir(tmp_path / "maildir")
    key = box.add(wire("representations"))

    assert isinstance(box.get_message(key), mailbox.MaildirMessage)
    assert b"Subject: representations" in box.get_bytes(key)
    assert "Subject: representations" in box.get_string(key)
    with box.get_file(key) as stream:
        assert isinstance(stream.read(), bytes)


def test_factory_controls_mapping_reads_without_changing_explicit_raw_getters(tmp_path):
    path = tmp_path / "maildir"
    writer = mailbox.Maildir(path)
    writer.add(wire("factory"))
    writer.close()

    def subject_factory(stream):
        for line in stream:
            if line.lower().startswith(b"subject:"):
                return line.split(b":", 1)[1].strip().decode()
        return None

    reader = mailbox.Maildir(path, factory=subject_factory, create=False)
    key = reader.keys()[0]
    assert reader[key] == "factory"
    assert reader.get(key) == "factory"
    assert b"Subject: factory" in reader.get_bytes(key)


# Mailbox 的替换、删除、update、pop 与 clear 语义。
#
# __setitem__ 只能替换既有 key；对普通替换消息，原有格式状态应保留。remove/del 缺 key 抛错，
# discard 则适合面对并发删除。update 也不能创建新 key，且失败前已完成的替换不会回滚，因此它
# 不是事务。pop/popitem/clear 与映射类似，但返回值仍经过邮箱 factory。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# MaildirMessage 的 new/cur、info、flags、delivery date 与落盘状态。
#
# Maildir 把是否已被邮箱看到（cur/new）与是否已读（S flag）分开。标准 info 形如 ``2,FS``，
# flags 按字母排序；实验性 info 不解释为 flags，add_flag 会把它覆盖成标准 ``2,`` 格式。
# delivery date 最终由消息文件 mtime 表示，因此比较时要考虑文件系统时间精度。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# Maildir folder、过期 tmp 清理，以及无锁即时写入生命周期。
#
# Maildir folder 以独立 Maildir 表示；非空 folder 不能删除。clean 只移除超过 36 小时的 tmp
# 文件，本例用固定旧时间戳而不 sleep。Maildir 每次变更立即落盘，不保持打开文件，也不需要
# 邮箱级锁，所以 flush/lock/unlock/close 都是兼容通用接口的 no-op。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# mboxMessage 的 envelope From、flags，以及单文件邮箱的锁与转义。
#
# mbox 用 ``From `` 行分隔消息，因此正文行若也以 ``From `` 开头，生成器会写成 ``>From ``；
# 这是格式要求，不是正文业务转义。状态 flags 分布在 Status/X-Status headers。单文件邮箱修改前
# 应 lock，flush 才保证待处理替换写回磁盘，get_file 视图不能跨 flush/close 长期保存。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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



FROM_LINE_420 = "sender@example.test Sat Jan  1 00:00:00 2000"


def test_mbox_message_manages_envelope_line_and_conventional_flags():
    message = mailbox.mboxMessage("Subject: state\n\nbody\n")
    message.set_from(FROM_LINE_420)
    message.set_flags("RODFA")

    assert message.get_from() == FROM_LINE_420
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
    message.set_from(FROM_LINE_420)
    message.set_flags("RF")

    box.lock()
    try:
        key = box.add(message)
        box.flush()
    finally:
        box.unlock()

    raw = path.read_bytes()
    assert raw.startswith(f"From {FROM_LINE_420}\n".encode())
    assert b"\n>From body is not a delimiter\n" in raw
    stored = box.get_message(key)
    assert stored.get_from() == FROM_LINE_420
    assert stored.get_flags() == "RF"
    with box.get_file(key) as view:
        assert b"Subject: escaped" in view.read()
    box.close()

    reopened = mailbox.mbox(path, create=False)
    assert reopened[key]["Subject"] == "escaped"
    reopened.close()


# MMDFMessage 状态与 Control-A 分隔的单文件邮箱。
#
# MMDFMessage 与 mboxMessage 共享 envelope From 和 R/O/D/F/A flags，MMDF 另用四个 Control-A
# 字符组成的行分隔消息。CPython 3.10 的 MMDF 与 mbox 共用 writer，仍会把正文 ``From `` 写成
# ``>From ``；读取这种原始格式时不能假定只因有 Control-A 分隔就不会出现 mbox 风格转义。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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



FROM_LINE_421 = "sender@example.test Sat Jan  1 00:00:00 2000"


def test_mmdf_message_uses_the_same_envelope_and_flag_model_as_mbox():
    message = mailbox.MMDFMessage("Subject: state\n\nbody\n")
    message.set_from(FROM_LINE_421)
    message.set_flags("RODFA")
    message.remove_flag("OD")
    message.add_flag("OD")

    assert message.get_from() == FROM_LINE_421
    assert set(message.get_flags()) == set("RODFA")
    assert set(message["Status"]) == set("RO")
    assert set(message["X-Status"]) == set("DFA")


def test_mmdf_file_workflow_persists_control_a_delimiters_and_format_state(tmp_path):
    path = tmp_path / "messages.mmdf"
    box = mailbox.MMDF(path)
    message = mailbox.MMDFMessage(
        "Subject: delimited\n\nbefore\nFrom remains ordinary body text\nafter\n"
    )
    message.set_from(FROM_LINE_421)
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
    assert stored.get_from() == FROM_LINE_421
    assert stored.get_flags() == "RF"
    with box.get_file(key) as view:
        assert b"Subject: delimited" in view.read()
    box.close()

    reopened = mailbox.MMDF(path, create=False)
    assert reopened[key]["Subject"] == "delimited"
    reopened.close()


# MHMessage sequences、MH folder 与 pack 重新编号。
#
# MH 每封消息是以数字命名的独立文件，状态由任意命名的 sequence 表示。Mailbox.set_sequences
# 一次重写 ``.mh_sequences``；pack 消除编号空洞并同步 sequence，但会让此前发出的旧 key 失效。
# MH 删除立即发生，不采用传统的逗号前缀软删除；普通内容改动也即时落盘。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# BabylMessage labels、visible headers 与独立的 get_file 视图。
#
# Babyl 同时存原始 header 和供 Rmail 展示的 visible header；修改原始 header 不会自动同步，
# 必须调用 update_visible。标准 labels 表示 unseen/deleted/answered 等状态，用户自定义 label 可由
# Babyl.get_labels 汇总。其 get_file 会复制成 BytesIO，所以即使邮箱关闭，已取得的视图仍独立。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.mailbox.Babyl
# polyglot-covers: python.mailbox.BabylMessage
# polyglot-covers: python.mailbox.BabylMessage.get_labels
# polyglot-covers: python.mailbox.BabylMessage.set_labels
# polyglot-covers: python.mailbox.BabylMessage.add_label
# polyglot-covers: python.mailbox.BabylMessage.remove_label
# polyglot-covers: python.mailbox.BabylMessage.get_visible
# polyglot-covers: python.mailbox.BabylMessage.set_visible
# polyglot-covers: python.mailbox.BabylMessage.update_visible
# polyglot-covers: python.mailbox.Babyl-visible-not-automatically-synchronized
# polyglot-covers: python.mailbox.Babyl.get_labels
# polyglot-covers: python.mailbox.Babyl.lock
# polyglot-covers: python.mailbox.Babyl.unlock
# polyglot-covers: python.mailbox.Babyl.flush
# polyglot-covers: python.mailbox.Babyl.close
# polyglot-covers: python.mailbox.Babyl.get_file-independent-bytesio



def test_babyl_message_updates_labels_and_synchronizes_visible_headers_explicitly():
    message = mailbox.BabylMessage("Subject: original\nTo: old@example.test\n\nbody\n")
    message.set_labels(["unseen", "project"])
    message.add_label("answered")
    message.remove_label("unseen")

    visible = Message()
    visible["Subject"] = "stale"
    visible["X-Visible-Only"] = "remove me"
    message.set_visible(visible)
    assert message.get_visible()["Subject"] == "stale"

    message.replace_header("Subject", "updated")
    message.update_visible()
    synchronized = message.get_visible()
    assert message.get_labels() == ["project", "answered"]
    assert synchronized["Subject"] == "updated"
    assert synchronized["To"] == "old@example.test"
    assert synchronized["X-Visible-Only"] is None
    assert synchronized.get_payload() is None


def test_babyl_mailbox_reports_custom_labels_and_file_view_survives_close(tmp_path):
    path = tmp_path / "rmail.babyl"
    box = mailbox.Babyl(path)
    message = mailbox.BabylMessage("Subject: stored\n\nbody\n")
    message.set_labels(["unseen", "project"])

    box.lock()
    try:
        key = box.add(message)
        box.flush()
    finally:
        box.unlock()
    assert box.get_labels() == ["project"]

    box.close()

    # Babyl 写入后的内存 TOC 与重读文件得到的 TOC 表示略有不同；文件视图应从重新扫描后的
    # mailbox 获取。get_file 返回独立 BytesIO，所以 mailbox 关闭后仍可读取。
    reopened = mailbox.Babyl(path, create=False)
    view = reopened.get_file(key)
    assert reopened.get_message(key).get_labels() == ["unseen", "project"]
    reopened.close()
    try:
        assert b"Subject: stored" in view.read()
    finally:
        view.close()


# Maildir 与 mbox/MMDF 之间的格式状态转换表。
#
# 格式消息构造器不只复制 headers/body，还尽可能转换状态：Maildir S/F/R/T 对应单文件格式的
# R/F/A/D，cur 对应 O。反向转换时 Status/X-Status 被消费并从普通 headers 移除；mbox 与
# MMDF 的 From 行和五种 flags 则可直接互转。不了解这一步会造成“复制后状态 header 消失”的误判。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# MH sequence、Babyl label 与 Maildir/mbox flags 的状态转换。
#
# unseen、replied、flagged 等概念在不同格式里分别是 sequence、label 或 flag。构造目标格式消息时，
# 标准库只转换有公认对应关系的状态：例如 Maildir 无 S 变 MH/Babyl unseen，P 只在 Babyl 中成为
# forwarded。自定义 sequence/label 没有通用映射，会在跨格式转换中丢失。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# mailbox.Message 输入复制，以及 NoSuch/NotEmpty/Clash/Format 异常。
#
# mailbox.Message 可从 email Message、str、bytes、二进制文件对象构造，且从 Message 构造是内容
# 复制而不是共享 headers。mailbox 专用异常区分路径不存在、目录非空、外部锁冲突和格式损坏；
# 处理邮件正文解析错误时不要误把这些存储层异常都吞成同一种失败。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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
