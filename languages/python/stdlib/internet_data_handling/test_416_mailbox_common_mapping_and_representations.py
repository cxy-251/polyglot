"""416｜Mailbox 通用映射接口、输入形态与消息表示。

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
