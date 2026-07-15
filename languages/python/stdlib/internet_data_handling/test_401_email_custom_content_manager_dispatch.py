"""401｜ContentManager 的 MIME get fallback 与 Python type/MRO set dispatch。

get handler 按 full MIME type → maintype → 空字符串查找；set handler 先查精确 type/名称，再沿 MRO，
最后查 None fallback。set_content 会先 clear_content，避免旧 payload/header 混入新表示；multipart
禁止直接替换内容。注册表没有匹配项时抛 KeyError，而不是猜测序列化方式。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.contentmanager.ContentManager
# polyglot-covers: python.email.contentmanager.add_get_handler
# polyglot-covers: python.email.contentmanager.get_content
# polyglot-covers: python.email.content-manager-get-full-mimetype-precedence
# polyglot-covers: python.email.content-manager-get-maintype-fallback
# polyglot-covers: python.email.content-manager-get-empty-fallback
# polyglot-covers: python.email.contentmanager.add_set_handler
# polyglot-covers: python.email.contentmanager.set_content
# polyglot-covers: python.email.content-manager-set-mro-dispatch
# polyglot-covers: python.email.content-manager-set-none-fallback
# polyglot-covers: python.email.content-manager-clears-old-content-first
# polyglot-covers: python.email.content-manager-no-handler-keyerror
# polyglot-covers: python.email.content-manager-multipart-typeerror

from email.contentmanager import ContentManager
from email.message import EmailMessage

import pytest


class Note:
    def __init__(self, text):
        self.text = text


class SpecialNote(Note):
    pass


def _set_note(message, note, *, subtype="x-note"):
    message["Content-Type"] = f"text/{subtype}; charset=utf-8"
    message.set_payload(note.text)


def test_set_dispatch_walks_mro_and_clears_previous_content():
    manager = ContentManager()
    manager.add_set_handler(Note, _set_note)
    manager.add_set_handler(
        None,
        lambda message, value: (
            message.__setitem__("Content-Type", "application/x-fallback"),
            message.set_payload(repr(value)),
        ),
    )

    message = EmailMessage()
    message.set_content("old")
    message.set_content(SpecialNote("new note"), content_manager=manager)
    assert message.get_content_type() == "text/x-note"
    assert message.get_payload() == "new note"
    assert str(message["MIME-Version"]) == "1.0"

    fallback = EmailMessage()
    fallback.set_content(object(), content_manager=manager)
    assert fallback.get_content_type() == "application/x-fallback"
    assert fallback.get_payload().startswith("<object object")


def test_get_dispatch_prefers_full_type_then_main_type_then_empty_key():
    manager = ContentManager()
    manager.add_get_handler("text/x-note", lambda message: "full")
    manager.add_get_handler("text", lambda message: "main")
    manager.add_get_handler("", lambda message: "fallback")

    def part(content_type):
        message = EmailMessage()
        message["Content-Type"] = content_type
        message.set_payload("raw")
        return message

    assert manager.get_content(part("text/x-note")) == "full"
    assert manager.get_content(part("text/x-other")) == "main"
    assert manager.get_content(part("application/x-other")) == "fallback"


def test_missing_handlers_and_multipart_set_are_explicit_errors():
    manager = ContentManager()
    message = EmailMessage()
    message["Content-Type"] = "application/x-unknown"
    with pytest.raises(KeyError):
        manager.get_content(message)
    with pytest.raises(KeyError):
        manager.set_content(message, object())

    manager.add_set_handler(Note, _set_note)
    multipart = EmailMessage()
    multipart.make_mixed()
    with pytest.raises(TypeError):
        manager.set_content(multipart, Note("not allowed"))
