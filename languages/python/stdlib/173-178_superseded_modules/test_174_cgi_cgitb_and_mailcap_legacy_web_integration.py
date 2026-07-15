"""174｜cgi、cgitb 与 mailcap：旧式网关表单、错误页和 MIME 启动规则。

cgi/cgitb 面向服务器直接执行脚本的 CGI 模型，mailcap 把 MIME 类型映射为
shell 命令。3.10 仍保留这些接口以兼容旧部署；案例覆盖解析和渲染，
但不会执行 mailcap 命令。现代服务应使用 Web 框架、email/urllib.parse 和
显式进程参数。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.cgi python.cgi.field-storage
# polyglot-covers: python.cgi.get-query python.cgi.url-encoded-post
# polyglot-covers: python.cgi.keep-blank-values python.cgi.repeated-fields
# polyglot-covers: python.cgi.getfirst-getlist python.cgi.mini-field-storage
# polyglot-covers: python.cgi.multipart python.cgi.file-upload
# polyglot-covers: python.cgi.parse-multipart python.cgi.parse-header
# polyglot-covers: python.cgi.maxlen python.cgi.max-num-fields
# polyglot-covers: python.stdlib.cgitb python.cgitb.html python.cgitb.text
# polyglot-covers: python.cgitb.hook python.cgitb.logging
# polyglot-covers: python.cgitb.enable python.cgitb.display-vs-log
# polyglot-covers: python.stdlib.mailcap python.mailcap.readmailcapfile
# polyglot-covers: python.mailcap.getcaps python.mailcap.listmailcapfiles
# polyglot-covers: python.mailcap.findmatch python.mailcap.wildcard
# polyglot-covers: python.mailcap.percent-substitution
# polyglot-covers: python.mailcap.shell-command-risk

import cgi
import cgitb
import io
import mailcap
import sys

import pytest


def get_environ(query):
    return {
        "REQUEST_METHOD": "GET",
        "QUERY_STRING": query,
    }


def post_environ(content_type, body):
    return {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
    }


def test_fieldstorage_parses_get_query_repetition_and_blank_values():
    form = cgi.FieldStorage(
        fp=io.BytesIO(),
        environ=get_environ("tag=python&tag=stdlib&empty="),
        keep_blank_values=True,
    )

    assert set(form.keys()) == {"tag", "empty"}
    assert "tag" in form
    assert form.getfirst("tag") == "python"
    assert form.getlist("tag") == ["python", "stdlib"]
    assert form.getfirst("empty") == ""

    repeated = form["tag"]
    assert isinstance(repeated, list)
    assert all(isinstance(item, cgi.MiniFieldStorage) for item in repeated)
    # 直接 form[name] 的返回类型会随重复次数改变；
    # 业务代码优先用 getfirst/getlist。


def test_fieldstorage_urlencoded_post_uses_content_length_not_stream_eof():
    body = b"name=Alice+Example&active=yes"
    stream = io.BytesIO(body + b"ignored=outside-request")
    form = cgi.FieldStorage(
        fp=stream,
        environ=post_environ(
            "application/x-www-form-urlencoded",
            body,
        ),
    )

    assert form.getfirst("name") == "Alice Example"
    assert form.getfirst("active") == "yes"
    assert "ignored" not in form
    assert stream.tell() == len(body)


def test_fieldstorage_separator_is_explicit_in_python_310():
    ordinary = cgi.FieldStorage(
        fp=io.BytesIO(),
        environ=get_environ("first=1;second=2"),
    )
    semicolon = cgi.FieldStorage(
        fp=io.BytesIO(),
        environ=get_environ("first=1;second=2"),
        separator=";",
    )

    assert ordinary.getfirst("first") == "1;second=2"
    assert "second" not in ordinary
    assert semicolon.getfirst("first") == "1"
    assert semicolon.getfirst("second") == "2"
    # 3.10 不再默认把分号和 & 同时视为分隔符，避免歧义和参数污染。


def test_fieldstorage_multipart_exposes_text_and_uploaded_file_metadata():
    boundary = b"POLYGLOT-BOUNDARY"
    body = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="title"\r\n'
        b"\r\n"
        b"lesson\r\n"
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="upload"; filename="note.txt"\r\n'
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"file bytes\r\n"
        b"--" + boundary + b"--\r\n"
    )
    content_type = "multipart/form-data; boundary=" + boundary.decode()

    form = cgi.FieldStorage(
        fp=io.BytesIO(body),
        environ=post_environ(content_type, body),
    )

    assert form.getfirst("title") == "lesson"
    upload = form["upload"]
    assert upload.name == "upload"
    assert upload.filename == "note.txt"
    assert upload.type == "text/plain"
    assert upload.file.read() == b"file bytes"
    # 上传内容在 file 中；不要因 value 看起来方便，
    # 就把任意大文件全部读进内存。


def test_parse_multipart_returns_lists_for_every_field():
    boundary = b"BOUNDARY-174"
    body = (
        b"--BOUNDARY-174\r\n"
        b'Content-Disposition: form-data; name="tag"\r\n\r\n'
        b"one\r\n"
        b"--BOUNDARY-174\r\n"
        b'Content-Disposition: form-data; name="tag"\r\n\r\n'
        b"two\r\n"
        b"--BOUNDARY-174--\r\n"
    )

    parsed = cgi.parse_multipart(
        io.BytesIO(body),
        {"boundary": boundary},
    )

    assert parsed == {"tag": ["one", "two"]}


@pytest.mark.parametrize(
    ("header", "main", "parameters"),
    [
        (
            'text/plain; charset="utf-8"; format=flowed',
            "text/plain",
            {"charset": "utf-8", "format": "flowed"},
        ),
        (
            'form-data; name="upload"; filename="a;b.txt"',
            "form-data",
            {"name": "upload", "filename": "a;b.txt"},
        ),
    ],
)
def test_parse_header_preserves_quoted_semicolons(header, main, parameters):
    assert cgi.parse_header(header) == (main, parameters)


def test_fieldstorage_limits_total_body_size_and_field_count(monkeypatch):
    body = b"first=1&second=2"
    monkeypatch.setattr(cgi, "maxlen", 5)
    with pytest.raises(ValueError, match="Maximum content length exceeded"):
        cgi.FieldStorage(
            fp=io.BytesIO(body),
            environ=post_environ(
                "application/x-www-form-urlencoded",
                body,
            ),
        )

    monkeypatch.setattr(cgi, "maxlen", 0)
    with pytest.raises(ValueError, match="Max number of fields exceeded"):
        cgi.FieldStorage(
            fp=io.BytesIO(),
            environ=get_environ("first=1&second=2"),
            max_num_fields=1,
        )


def captured_exception_info():
    try:
        return 1 / 0
    except ZeroDivisionError:
        return sys.exc_info()


def test_cgitb_text_and_html_render_the_same_exception_for_different_clients():
    info = captured_exception_info()
    text = cgitb.text(info, context=1)
    html = cgitb.html(info, context=1)

    assert "ZeroDivisionError" in text
    assert "division by zero" in text
    assert "<body" in html.lower()
    assert "ZeroDivisionError" in html
    assert "division by zero" in html
    # html 可能包含局部变量 repr；生产错误页不应直接向不可信客户端公开。


def test_cgitb_hook_can_hide_display_but_save_a_diagnostic_file(tmp_path):
    output = io.StringIO()
    handler = cgitb.Hook(
        display=0,
        logdir=str(tmp_path),
        context=1,
        file=output,
        format="text",
    )

    assert handler.handle(captured_exception_info()) is None

    rendered = output.getvalue()
    assert "A problem occurred" in rendered
    logs = list(tmp_path.iterdir())
    assert len(logs) == 1
    logged = logs[0].read_text(encoding="utf-8")
    assert "ZeroDivisionError" in logged
    assert "division by zero" in logged


def test_cgitb_enable_installs_a_hook_and_callers_must_restore_global_state():
    original = sys.excepthook
    try:
        assert cgitb.enable(display=0, format="text") is None
        assert isinstance(sys.excepthook, cgitb.Hook)
        assert sys.excepthook.display == 0
        assert sys.excepthook.format == "text"
    finally:
        sys.excepthook = original


def sample_mailcap_text():
    return io.StringIO(
        "text/plain; viewer --plain %s; description=Plain text\n"
        "text/*; viewer --type %t --charset %{charset} %% %s\n"
        "application/x-demo; demo-viewer %s; compose=demo-editor %s\n"
    )


def test_readmailcapfile_builds_a_list_of_entries_per_mime_type():
    caps = mailcap.readmailcapfile(sample_mailcap_text())

    assert set(caps) == {"text/plain", "text/*", "application/x-demo"}
    assert caps["text/plain"] == [
        {"view": "viewer --plain %s", "description": "Plain text"}
    ]
    assert caps["application/x-demo"][0]["compose"] == "demo-editor %s"


def test_getcaps_merges_files_in_listmailcapfiles_order(tmp_path, monkeypatch):
    first = tmp_path / "first.mailcap"
    second = tmp_path / "second.mailcap"
    first.write_text("text/plain; first-view %s\n", encoding="utf-8")
    second.write_text("text/plain; second-view %s\n", encoding="utf-8")
    monkeypatch.setattr(
        mailcap,
        "listmailcapfiles",
        lambda: [str(first), str(second)],
    )

    caps = mailcap.getcaps()

    assert [entry["view"] for entry in caps["text/plain"]] == [
        "first-view %s",
        "second-view %s",
    ]


def test_findmatch_prefers_exact_type_then_wildcard_and_substitutes_fields():
    caps = mailcap.readmailcapfile(sample_mailcap_text())

    exact_command, exact_entry = mailcap.findmatch(
        caps,
        "text/plain",
        filename="lesson-file.txt",
        plist=["charset=utf-8"],
    )
    wildcard_command, wildcard_entry = mailcap.findmatch(
        caps,
        "text/markdown",
        filename="README.md",
        plist=["charset=utf-8"],
    )

    assert exact_command == "viewer --plain lesson-file.txt"
    assert exact_entry["description"] == "Plain text"
    assert wildcard_command == (
        "viewer --type text/markdown --charset utf-8 % README.md"
    )
    assert wildcard_entry is caps["text/*"][0]


def test_findmatch_returns_none_pair_when_no_entry_matches():
    caps = mailcap.readmailcapfile(sample_mailcap_text())
    assert mailcap.findmatch(caps, "image/png") == (None, None)


def test_mailcap_commands_are_shell_text_and_must_not_be_executed_blindly():
    caps = mailcap.readmailcapfile(sample_mailcap_text())
    with pytest.warns(mailcap.UnsafeMailcapInput, match="Refusing"):
        result = mailcap.findmatch(
            caps,
            "application/x-demo",
            filename="$(touch should-not-run)",
        )

    assert result == (None, None)
    # 3.10.8 起会拒绝不安全注入值；但安全字符得到的结果仍是 shell 文本，
    # 而且 entry 的 test 字段会调用 os.system，
    # 所以仍不能盲目处理不可信 mailcap。
