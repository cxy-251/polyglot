"""423｜BabylMessage labels、visible headers 与独立的 get_file 视图。

Babyl 同时存原始 header 和供 Rmail 展示的 visible header；修改原始 header 不会自动同步，
必须调用 update_visible。标准 labels 表示 unseen/deleted/answered 等状态，用户自定义 label 可由
Babyl.get_labels 汇总。其 get_file 会复制成 BytesIO，所以即使邮箱关闭，已取得的视图仍独立。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from email.message import Message
import mailbox


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

    view = box.get_file(key)
    box.close()
    try:
        assert b"Subject: stored" in view.read()
    finally:
        view.close()

    reopened = mailbox.Babyl(path, create=False)
    assert reopened.get_message(key).get_labels() == ["unseen", "project"]
    reopened.close()
