"""107｜EmailMessage header 是有序、大小写不敏感、允许重复的“类 mapping”。

header 按原始大小写与插入顺序保存，查找不区分大小写；``msg[name]`` 缺失返回 None 而非
KeyError。普通字段赋值是 append，不是 dict 式覆盖；重复字段必须用 get_all。标准 policy 会限制
Subject 等 unique header，更新它们应使用 replace_header 或先删除再添加。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.EmailMessage
# polyglot-covers: python.email.header-mapping-case-insensitive
# polyglot-covers: python.email.header-case-preserved
# polyglot-covers: python.email.header-order-preserved
# polyglot-covers: python.email.header-duplicates-allowed
# polyglot-covers: python.email.header-setitem-appends
# polyglot-covers: python.email.header-getitem-missing-none
# polyglot-covers: python.email.header-get-all
# polyglot-covers: python.email.header-delete-all-occurrences
# polyglot-covers: python.email.header-replace-preserves-position-and-case
# polyglot-covers: python.email.header-replace-missing-keyerror
# polyglot-covers: python.email.unique-header-duplicate-valueerror
# polyglot-covers: python.email.header-newline-injection-valueerror




from email.headerregistry import BaseHeader
from email.message import EmailMessage
import pytest
from email import policy
from email.parser import BytesParser
from email.contentmanager import raw_data_manager
from email.headerregistry import BaseHeader, HeaderRegistry
from email.contentmanager import ContentManager
from email.message import EmailMessage, MIMEPart
from email.errors import HeaderParseError

def test_header_mapping_preserves_order_case_and_duplicate_fields():
    message = EmailMessage()
    message["Received"] = "by first.example"
    message["Subject"] = "status"
    message["received"] = "by second.example"

    assert len(message) == 3
    assert message.keys() == ["Received", "Subject", "received"]
    assert "RECEIVED" in message
    assert message["missing"] is None
    assert message.get("missing", "fallback") == "fallback"
    assert [str(value) for value in message.get_all("RECEIVED")] == [
        "by first.example",
        "by second.example",
    ]
    assert all(isinstance(value, BaseHeader) for value in message.values())

    del message["received"]
    assert "Received" not in message
    assert message.keys() == ["Subject"]
    del message["not-present"]  # 与 dict 不同，删除缺失 header 不抛异常。


def test_replace_header_updates_in_place_while_assignment_appends_or_is_limited():
    message = EmailMessage()
    message["X-Trace"] = "old"
    message["Subject"] = "first"
    message["X-Tail"] = "last"

    message.replace_header("x-trace", "new")
    assert message.keys() == ["X-Trace", "Subject", "X-Tail"]
    assert str(message["X-Trace"]) == "new"
    with pytest.raises(KeyError):
        message.replace_header("X-Missing", "value")

    with pytest.raises(ValueError, match="at most 1"):
        message["Subject"] = "second"
    del message["subject"]
    message["subject"] = "second"
    assert message.keys() == ["X-Trace", "X-Tail", "subject"]


def test_default_policy_rejects_crlf_header_injection():
    message = EmailMessage()
    with pytest.raises(ValueError, match="linefeed|carriage return"):
        message["Subject"] = "safe\nBcc: injected@example.com"


# raw_data_manager 的 text/binary 内容、CTE 与附件元数据。
#
# set_content(str) 建立 text/*、charset 与合适的 Content-Transfer-Encoding，get_content 自动解码为
# Unicode；bytes 必须显式给 maintype/subtype，默认 base64，get_content 返回原 bytes。filename 会
# 隐式创建 attachment disposition。clear_content 只移除 payload 与 Content-*，clear 才清空全部。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.contentmanager.raw_data_manager
# polyglot-covers: python.email.message.set_content
# polyglot-covers: python.email.message.get_content
# polyglot-covers: python.email.set-content-str-text-plain
# polyglot-covers: python.email.set-content-text-charset
# polyglot-covers: python.email.set-content-text-cte
# polyglot-covers: python.email.set-content-bytes-requires-mimetype
# polyglot-covers: python.email.set-content-bytes-default-base64
# polyglot-covers: python.email.set-content-filename-implies-attachment
# polyglot-covers: python.email.set-content-cid-params-headers
# polyglot-covers: python.email.get_content_type
# polyglot-covers: python.email.get_content_maintype
# polyglot-covers: python.email.get_content_subtype
# polyglot-covers: python.email.get_content_charset
# polyglot-covers: python.email.get_charsets
# polyglot-covers: python.email.get_content_disposition
# polyglot-covers: python.email.is_attachment
# polyglot-covers: python.email.clear_content
# polyglot-covers: python.email.clear
# polyglot-covers: python.email.clear-content-keeps-non-content-headers




def test_text_content_is_encoded_for_transport_and_decoded_for_application_use():
    message = EmailMessage()
    message["Subject"] = "text"
    message.set_content("你好", charset="utf-8", cte="quoted-printable")

    assert message.get_content_type() == "text/plain"
    assert message.get_content_maintype() == "text"
    assert message.get_content_subtype() == "plain"
    assert message.get_content_charset() == "utf-8"
    assert message.get_charsets() == ["utf-8"]
    assert str(message["Content-Transfer-Encoding"]) == "quoted-printable"
    assert message.get_content() == "你好\n"
    assert message.get_payload(decode=True) == "你好\n".encode("utf-8")

    with pytest.raises(ValueError):
        EmailMessage().set_content("你好", cte="7bit")


def test_binary_content_requires_type_and_carries_attachment_metadata():
    payload = b"\0\xffbinary"
    message = EmailMessage()
    message["X-Owner"] = "polyglot"
    with pytest.raises(TypeError):
        message.set_content(payload)

    message.set_content(
        payload,
        maintype="application",
        subtype="octet-stream",
        filename="数据.bin",
        cid="<blob@example.test>",
        params={"x-format": "demo"},
        headers=["X-Part: one"],
    )
    assert message.get_content() == payload
    assert str(message["Content-Transfer-Encoding"]) == "base64"
    assert message.get_content_disposition() == "attachment"
    assert message.is_attachment() is True
    assert message.get_filename() == "数据.bin"
    assert str(message["Content-ID"]) == "<blob@example.test>"
    assert message["Content-Type"].params["x-format"] == "demo"
    assert str(message["X-Part"]) == "one"

    message.clear_content()
    assert message.get_payload() is None
    assert "Content-Type" not in message
    assert "Content-Disposition" not in message
    assert "X-Owner" in message
    assert "MIME-Version" in message
    message.clear()
    assert len(message) == 0


# plain/html/related/attachment 组成的 MIME 树与 body 选择。
#
# add_alternative 把现有正文移入 multipart/alternative；HTML part 的 add_related 再建立
# multipart/related 并把图片默认标为 inline；add_attachment 最外层建立 multipart/mixed。get_body
# 按 related/html/plain 偏好选候选，iter_parts 只看直接子项，walk 深度优先遍历整棵树。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# make_related/make_alternative/make_mixed 的逐层转换与 boundary。
#
# make_* 会把现有 Content-* 与 payload 移进新的第一个子 part，而不是丢弃正文；只允许按
# non-multipart → related → alternative → mixed 的兼容方向转换。显式 boundary 便于可重复 fixture，
# 生产代码通常留空，让 generator 在首次 flatten 时生成唯一值。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.message.make_related
# polyglot-covers: python.email.message.make_alternative
# polyglot-covers: python.email.message.make_mixed
# polyglot-covers: python.email.make-multipart-moves-existing-content-first
# polyglot-covers: python.email.make-multipart-explicit-boundary
# polyglot-covers: python.email.get_boundary
# polyglot-covers: python.email.invalid-multipart-conversion-typeerror
# polyglot-covers: python.email.message.preamble
# polyglot-covers: python.email.message.epilogue
# polyglot-covers: python.email.multipart-preamble-epilogue-outside-boundaries




def test_explicit_conversions_keep_the_existing_tree_as_the_first_part():
    message = EmailMessage()
    message.set_content("root body")

    message.make_related(boundary="RELATED-BOUNDARY")
    assert message.get_content_type() == "multipart/related"
    assert message.get_boundary() == "RELATED-BOUNDARY"
    assert list(message.iter_parts())[0].get_content().strip() == "root body"

    message.make_alternative(boundary="ALTERNATIVE-BOUNDARY")
    assert message.get_content_type() == "multipart/alternative"
    assert message.get_boundary() == "ALTERNATIVE-BOUNDARY"
    assert list(message.iter_parts())[0].get_content_type() == "multipart/related"

    message.make_mixed(boundary="MIXED-BOUNDARY")
    assert message.get_content_type() == "multipart/mixed"
    assert message.get_boundary() == "MIXED-BOUNDARY"
    assert list(message.iter_parts())[0].get_content_type() == "multipart/alternative"


def test_mixed_container_cannot_be_converted_back_to_related_or_alternative():
    message = EmailMessage()
    message.make_mixed()
    with pytest.raises(ValueError, match="Cannot convert mixed to related"):
        message.make_related()
    with pytest.raises(ValueError, match="Cannot convert mixed to alternative"):
        message.make_alternative()


def test_preamble_and_epilogue_round_trip_outside_multipart_boundaries():
    message = EmailMessage()
    message.make_mixed(boundary="BOUNDARY")
    child = EmailMessage()
    child.set_content("inside")
    message.attach(child)
    message.preamble = "text before the first boundary"
    message.epilogue = "text after the closing boundary"

    wire = message.as_bytes(policy=policy.SMTP)
    assert b"text before the first boundary\r\n--BOUNDARY" in wire
    assert b"--BOUNDARY--\r\ntext after the closing boundary" in wire
    parsed = BytesParser(policy=policy.default).parsebytes(wire)
    assert parsed.preamble == "text before the first boundary"
    assert parsed.epilogue == "text after the closing boundary"


# EmailPolicy 不可变 clone、非交换组合与 transport 预设。
#
# policy 控制 parser factory、header 类型、fold、换行、CTE 与 defect 策略。实例不可变，修改必须
# clone；``left + right`` 采用 right 的非默认值，因此不满足交换律。default 内部用 LF，SMTP 使用
# RFC 要求的 CRLF，SMTPUTF8 还允许 RFC 6532 UTF-8 header；parser 应始终显式指定 policy。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.policy.Policy
# polyglot-covers: python.email.policy.EmailPolicy
# polyglot-covers: python.email.policy.default
# polyglot-covers: python.email.policy.compat32
# polyglot-covers: python.email.policy.SMTP
# polyglot-covers: python.email.policy.SMTPUTF8
# polyglot-covers: python.email.policy.HTTP
# polyglot-covers: python.email.policy.strict
# polyglot-covers: python.email.policy-immutable
# polyglot-covers: python.email.policy.clone
# polyglot-covers: python.email.policy-addition-noncommutative
# polyglot-covers: python.email.policy.linesep
# polyglot-covers: python.email.policy.max_line_length
# polyglot-covers: python.email.policy.cte_type
# polyglot-covers: python.email.policy.raise_on_defect
# polyglot-covers: python.email.policy.mangle_from
# polyglot-covers: python.email.policy.utf8
# polyglot-covers: python.email.policy.message_factory
# polyglot-covers: python.email.policy.header_factory
# polyglot-covers: python.email.policy.content_manager
# polyglot-covers: python.email.policy.header_max_count
# polyglot-covers: python.email.policy.header_source_parse
# polyglot-covers: python.email.policy.header_store_parse
# polyglot-covers: python.email.policy.header_fetch_parse
# polyglot-covers: python.email.policy.fold
# polyglot-covers: python.email.policy.fold_binary
# polyglot-covers: python.email.policy.verify_generated_headers-3.10.15




def test_policy_instances_are_immutable_and_clone_carries_explicit_changes():
    assert EmailMessage().policy is policy.default
    assert policy.default.linesep == "\n"
    assert policy.SMTP.linesep == "\r\n"
    assert policy.SMTPUTF8.utf8 is True
    assert policy.HTTP.max_line_length is None
    assert policy.strict.raise_on_defect is True
    assert policy.compat32.mangle_from_ is True

    customized = policy.default.clone(
        linesep="\r\n",
        max_line_length=60,
        cte_type="7bit",
        raise_on_defect=True,
    )
    assert customized is not policy.default
    assert customized.linesep == "\r\n"
    assert customized.max_line_length == 60
    assert customized.cte_type == "7bit"
    assert customized.raise_on_defect is True
    assert policy.default.max_line_length == 78
    with pytest.raises(AttributeError):
        policy.default.linesep = "\r\n"


def test_policy_addition_uses_right_hand_nondefault_values():
    length_100 = policy.compat32.clone(max_line_length=100)
    length_80 = policy.compat32.clone(max_line_length=80)
    assert (length_100 + length_80).max_line_length == 80
    assert (length_80 + length_100).max_line_length == 100


def test_email_policy_composes_factories_parsing_hooks_and_folding_protocols():
    assert isinstance(policy.default.message_factory(), EmailMessage)
    assert isinstance(policy.default.header_factory, HeaderRegistry)
    assert policy.default.content_manager is raw_data_manager
    assert policy.default.header_max_count("Subject") == 1
    assert policy.default.header_max_count("X-Repeatable") is None

    source_name, source_value = policy.default.header_source_parse(
        ["Subject: first line\n", "\tcontinued\n"]
    )
    stored_name, stored_value = policy.default.header_store_parse("Subject", "stored")
    fetched_value = policy.default.header_fetch_parse(source_name, source_value)
    assert source_name == stored_name == "Subject"
    assert isinstance(stored_value, BaseHeader)
    assert isinstance(fetched_value, BaseHeader)
    assert "first line" in str(fetched_value)
    assert "continued" in str(fetched_value)
    assert policy.default.fold(stored_name, stored_value) == "Subject: stored\n"
    assert policy.SMTP.fold_binary(stored_name, stored_value).endswith(b"\r\n")

    # 3.10.15 安全修复新增该开关；低于该补丁版本没有此属性。
    if hasattr(policy.default, "verify_generated_headers"):
        assert policy.default.verify_generated_headers is True


# as_string/as_bytes、UTF-8 表示、policy override 与 flatten 副作用。
#
# as_string 默认生成 7-bit-clean header，非 ASCII 用 encoded-word；str(msg) 临时 clone utf8=True，
# 用于可读展示而非直接 SMTP 发送。as_bytes/bytes 产生 binary。multipart boundary 可在首次 flatten
# 时补入并修改原对象，因此“只序列化”并非严格无副作用；需要稳定输出时应提前固定 boundary。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.message.as_string
# polyglot-covers: python.email.message.__str__
# polyglot-covers: python.email.as-string-seven-bit-clean
# polyglot-covers: python.email.str-message-utf8-readable
# polyglot-covers: python.email.message.as_bytes
# polyglot-covers: python.email.message.__bytes__
# polyglot-covers: python.email.serialization-policy-override
# polyglot-covers: python.email.smtp-crlf-lines
# polyglot-covers: python.email.flatten-may-generate-boundary
# polyglot-covers: python.email.flatten-can-mutate-message-trap
# polyglot-covers: python.email.set_unixfrom
# polyglot-covers: python.email.get_unixfrom
# polyglot-covers: python.email.serialize-unixfrom



def test_string_and_bytes_conveniences_use_different_unicode_and_line_policies():
    message = EmailMessage()
    message["From"] = "sender@example.test"
    message["Subject"] = "中文主题"
    message.set_content("正文")

    seven_bit = message.as_string()
    readable = str(message)
    assert "中文主题" not in seven_bit
    assert "=?utf-8?" in seven_bit.lower()
    assert "中文主题" in readable

    default_bytes = message.as_bytes()
    assert bytes(message) == default_bytes
    smtp_bytes = message.as_bytes(policy=policy.SMTP)
    assert b"\r\n" in smtp_bytes
    assert b"\n" not in smtp_bytes.replace(b"\r\n", b"")


def test_first_flatten_generates_and_stores_a_multipart_boundary():
    message = EmailMessage()
    message.set_content("plain")
    message.add_alternative("<p>html</p>", subtype="html")
    assert message.get_boundary() is None

    serialized = message.as_bytes()
    boundary = message.get_boundary()
    assert boundary is not None
    assert boundary.encode("ascii") in serialized
    assert message.as_bytes() == serialized


def test_unixfrom_is_envelope_metadata_outside_the_header_mapping():
    message = EmailMessage()
    message["Subject"] = "stored in mbox"
    message.set_content("body")
    assert message.get_unixfrom() is None
    message.set_unixfrom("From sender@example.test Sat Jan  1 00:00:00 2022")
    assert "unixfrom" not in message
    assert message.as_string(unixfrom=False).startswith("Subject:")
    assert message.as_string(unixfrom=True).startswith("From sender@example.test")


# ContentManager 的 MIME get fallback 与 Python type/MRO set dispatch。
#
# get handler 按 full MIME type → maintype → 空字符串查找；set handler 先查精确 type/名称，再沿 MRO，
# 最后查 None fallback。set_content 会先 clear_content，避免旧 payload/header 混入新表示；multipart
# 禁止直接替换内容。注册表没有匹配项时抛 KeyError，而不是猜测序列化方式。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# message/rfc822 的 list payload、is_multipart 与 MIMEPart 差异。
#
# 把 EmailMessage 作为内容会建立 message/rfc822，payload 是含一个子消息的 list，因此
# is_multipart=True，即使 maintype 不是 multipart；walk/iter_parts 仍会下降。EmailMessage.set_content
# 补 MIME-Version，而 MIMEPart 用于子 part，不自动加该 header，避免每层重复。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.message.MIMEPart
# polyglot-covers: python.email.mimepart-no-automatic-mime-version
# polyglot-covers: python.email.emailmessage-automatic-mime-version
# polyglot-covers: python.email.set-content-message-rfc822
# polyglot-covers: python.email.get-content-message-returns-message
# polyglot-covers: python.email.message-rfc822-list-payload
# polyglot-covers: python.email.is-multipart-based-on-list-payload
# polyglot-covers: python.email.message-maintype-can-be-multipart-behavior
# polyglot-covers: python.email.message-partial-requires-bytes
# polyglot-covers: python.email.message-rfc822-cte-restrictions




def test_mimepart_omits_top_level_mime_version_header():
    top_level = EmailMessage()
    top_level.set_content("body")
    part = MIMEPart()
    part.set_content("body")
    assert str(top_level["MIME-Version"]) == "1.0"
    assert part["MIME-Version"] is None


def test_nested_message_is_a_container_even_though_maintype_is_message():
    inner = EmailMessage()
    inner["Subject"] = "forwarded"
    inner.set_content("nested body")
    outer = EmailMessage()
    outer.set_content(inner)

    assert outer.get_content_type() == "message/rfc822"
    assert outer.get_content_maintype() == "message"
    assert outer.is_multipart() is True
    assert outer.get_payload() == [inner]
    assert list(outer.iter_parts()) == [inner]
    assert outer.get_content() is inner
    assert [part.get_content_type() for part in outer.walk()] == [
        "message/rfc822",
        "text/plain",
    ]


def test_message_partial_and_rfc822_reject_incompatible_object_cte_options():
    inner = EmailMessage()
    inner.set_content("nested")
    with pytest.raises(ValueError, match="message/partial is not supported"):
        EmailMessage().set_content(inner, subtype="partial")
    with pytest.raises(ValueError):
        EmailMessage().set_content(inner, cte="base64")


# RFC 2231 filename、Content-Type 参数、boundary、默认类型与手动 attach。
#
# add_header 会把非 ASCII filename 作为 RFC 2231 参数序列化，get_filename 返回解码且去引号值。
# set_param(replace=True) 与 set_boundary 原位重写 header；del_param 在 3.10 删除后重新追加，
# 不保证顺序和大小写。无 Content-Type 时 set_boundary 抛 HeaderParseError。default type 不是
# header，只影响缺失时的解释。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.email.message.add_header
# polyglot-covers: python.email.rfc2231-nonascii-filename
# polyglot-covers: python.email.get_filename
# polyglot-covers: python.email.get-filename-content-type-name-fallback
# polyglot-covers: python.email.set_param
# polyglot-covers: python.email.del_param
# polyglot-covers: python.email.set-param-replace-preserves-header-position
# polyglot-covers: python.email.set_boundary
# polyglot-covers: python.email.set-boundary-preserves-header-position
# polyglot-covers: python.email.set-boundary-without-content-type-error
# polyglot-covers: python.email.get_default_type
# polyglot-covers: python.email.set_default_type
# polyglot-covers: python.email.default-type-not-stored-as-header
# polyglot-covers: python.email.message.attach
# polyglot-covers: python.email.attach-requires-list-payload
# polyglot-covers: python.email.multipart-get-charsets-walk-order
# polyglot-covers: python.email.message.get_param
# polyglot-covers: python.email.message.get_params
# polyglot-covers: python.email.message.set_type
# polyglot-covers: python.email.set-type-adds-mime-version
# polyglot-covers: python.email.set-type-invalid-valueerror




def test_nonascii_filename_round_trips_and_serializes_as_rfc2231():
    message = EmailMessage()
    message.set_content(b"PDF", maintype="application", subtype="pdf")
    message.add_header("Content-Disposition", "attachment", filename="résumé.pdf")
    assert message.get_filename() == "résumé.pdf"
    serialized = message.as_bytes()
    assert b"filename*=utf-8''r%C3%A9sum%C3%A9.pdf" in serialized

    fallback = EmailMessage()
    fallback["Content-Type"] = 'application/octet-stream; name="fallback.bin"'
    assert fallback.get_filename() == "fallback.bin"


def test_parameter_replacement_and_boundary_preserve_position_but_deletion_reappends():
    message = EmailMessage()
    message["X-Before"] = "one"
    message["Content-Type"] = "text/plain; charset=utf-8"
    message["X-After"] = "two"

    message.set_param("format", "flowed", replace=True)
    assert message.keys() == ["X-Before", "Content-Type", "X-After"]
    assert message["Content-Type"].params["format"] == "flowed"

    message.set_boundary("boundary with space")
    assert message.get_boundary() == "boundary with space"
    assert message.keys() == ["X-Before", "Content-Type", "X-After"]

    # del_param 没有 replace=True 入口：3.10 通过删除再追加 header 实现，因此位置和字段名
    # 大小写都可能变化。若顺序有业务意义，应完成所有删除后再显式整理 header。
    message.del_param("format")
    assert "format" not in message["Content-Type"].params
    assert message.keys() == ["X-Before", "X-After", "content-type"]
    with pytest.raises(HeaderParseError):
        EmailMessage().set_boundary("missing content type")


def test_default_type_is_metadata_and_manual_attach_builds_a_list_payload():
    blank = EmailMessage()
    assert blank.get_default_type() == "text/plain"
    blank.set_default_type("message/rfc822")
    assert blank.get_content_type() == "message/rfc822"
    assert blank["Content-Type"] is None

    container = EmailMessage()
    container.make_mixed()
    text = EmailMessage()
    text.set_content("text", charset="utf-8")
    binary = EmailMessage()
    binary.set_content(b"bin", maintype="application", subtype="octet-stream")
    container.attach(text)
    container.attach(binary)
    assert container.get_charsets() == [None, "utf-8", None]

    scalar = EmailMessage()
    scalar.set_content("already scalar")
    with pytest.raises(TypeError):
        scalar.attach(EmailMessage())


def test_legacy_parameter_access_and_set_type_preserve_structured_mime_metadata():
    message = EmailMessage()
    message["Content-Type"] = 'text/plain; charset="utf-8"; format=flowed'

    assert message.get_param("CHARSET") == "utf-8"
    assert ("format", "flowed") in message.get_params()
    message.set_type("application/json")
    assert message.get_content_type() == "application/json"
    assert message.get_param("charset") == "utf-8"
    assert message["MIME-Version"] == "1.0"
    with pytest.raises(ValueError):
        message.set_type("missing-slash")
