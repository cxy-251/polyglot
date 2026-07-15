"""390｜plain/html/related/attachment 组成的 MIME 树与 body 选择。

add_alternative 把现有正文移入 multipart/alternative；HTML part 的 add_related 再建立
multipart/related 并把图片默认标为 inline；add_attachment 最外层建立 multipart/mixed。get_body
按 related/html/plain 偏好选候选，iter_parts 只看直接子项，walk 深度优先遍历整棵树。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.add_alternative
# polyglot-covers: python.email.message.add_related
# polyglot-covers: python.email.message.add_attachment
# polyglot-covers: python.email.add-related-default-inline
# polyglot-covers: python.email.add-attachment-default-attachment
# polyglot-covers: python.email.multipart-alternative
# polyglot-covers: python.email.multipart-related
# polyglot-covers: python.email.multipart-mixed
# polyglot-covers: python.email.message.get_body
# polyglot-covers: python.email.get-body-preference-list
# polyglot-covers: python.email.message.iter_parts
# polyglot-covers: python.email.message.iter_attachments
# polyglot-covers: python.email.message.walk
# polyglot-covers: python.email.walk-depth-first-includes-containers

from email.message import EmailMessage


def _build_rich_message():
    message = EmailMessage()
    message["Subject"] = "report"
    message.set_content("plain body")
    message.add_alternative("<p>html body</p>", subtype="html")

    html_part = list(message.iter_parts())[1]
    html_part.add_related(
        b"PNG",
        maintype="image",
        subtype="png",
        cid="<logo@example.test>",
    )
    message.add_attachment(
        b"PDF",
        maintype="application",
        subtype="pdf",
        filename="report.pdf",
    )
    return message


def test_add_methods_build_the_expected_nested_mime_tree_and_dispositions():
    message = _build_rich_message()
    assert message.get_content_type() == "multipart/mixed"
    immediate = list(message.iter_parts())
    assert [part.get_content_type() for part in immediate] == [
        "multipart/alternative",
        "application/pdf",
    ]
    assert immediate[1].is_attachment() is True
    assert immediate[1].get_filename() == "report.pdf"

    related = list(immediate[0].iter_parts())[1]
    assert related.get_content_type() == "multipart/related"
    image = list(related.iter_parts())[1]
    assert image.get_content_type() == "image/png"
    assert image.get_content_disposition() == "inline"
    assert image.get_content() == b"PNG"


def test_body_selection_attachment_iteration_and_walk_have_different_scope():
    message = _build_rich_message()
    assert message.get_body().get_content_type() == "multipart/related"
    assert message.get_body(("html", "plain")).get_content_type() == "text/html"
    assert message.get_body(("plain",)).get_content().strip() == "plain body"
    assert [part.get_filename() for part in message.iter_attachments()] == ["report.pdf"]
    assert [part.get_content_type() for part in message.walk()] == [
        "multipart/mixed",
        "multipart/alternative",
        "text/plain",
        "multipart/related",
        "text/html",
        "image/png",
        "application/pdf",
    ]
