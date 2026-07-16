"""130｜imaplib 与 nntplib 的邮箱状态机、命令结果和协议解析。

IMAP 用 tagged/untagged 响应维护邮箱状态；NNTP 使用三位状态码，
并用点终止多行数据。记录型客户端保留公开方法的参数整理和解析逻辑。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.imaplib python.imaplib.IMAP4-exceptions
# polyglot-covers: python.imaplib.Int2AP python.imaplib.ParseFlags
# polyglot-covers: python.imaplib.Internaldate2tuple python.imaplib.Time2Internaldate
# polyglot-covers: python.imaplib.IMAP4.login python.imaplib.password-always-quoted
# polyglot-covers: python.imaplib.IMAP4.select-examine python.imaplib.mailbox-state
# polyglot-covers: python.imaplib.IMAP4.search python.imaplib.utf8-search-charset-trap
# polyglot-covers: python.imaplib.IMAP4.fetch-store-copy-expunge
# polyglot-covers: python.imaplib.IMAP4.uid python.imaplib.uid-command-validation
# polyglot-covers: python.imaplib.IMAP4.append python.imaplib.append-literal-crlf
# polyglot-covers: python.imaplib.IMAP4.response-recent python.imaplib.untagged-response
# polyglot-covers: python.imaplib.IMAP4-context-manager python.imaplib.IMAP4_SSL
# polyglot-covers: python.stdlib.nntplib python.nntplib-deprecated-after-3.10
# polyglot-covers: python.nntplib.NNTPError-hierarchy python.nntplib.response-attribute
# polyglot-covers: python.nntplib.decode_header python.nntplib.GroupInfo-ArticleInfo
# polyglot-covers: python.nntplib.capabilities python.nntplib.group
# polyglot-covers: python.nntplib.stat-next-last python.nntplib.article-head-body
# polyglot-covers: python.nntplib.list-help-xhdr python.nntplib.overview-format
# polyglot-covers: python.nntplib.over-over-xover-fallback python.nntplib.date
# polyglot-covers: python.nntplib.post-dot-stuffing python.nntplib.context-manager

from datetime import datetime, timezone
from io import BytesIO

import imaplib
import nntplib
import pytest


def test_imap_helpers_encode_tags_flags_and_internal_dates():
    assert imaplib.Int2AP(0) == b""
    assert imaplib.Int2AP(15) == b"P"
    assert imaplib.Int2AP(16) == b"BA"

    response = b'* 23 FETCH (FLAGS (\\Seen \\Answered project))'
    assert imaplib.ParseFlags(response) == (b"\\Seen", b"\\Answered", b"project")

    parsed = imaplib.Internaldate2tuple(
        b'* 23 FETCH (INTERNALDATE "02-Jan-2024 03:04:05 +0000")'
    )
    # Internaldate2tuple 返回本地时间 struct_time，
    # 而不是保留原始 +0000 墙上时钟。
    expected_local = datetime(
        2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc
    ).astimezone()
    assert parsed[:6] == expected_local.timetuple()[:6]

    aware = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert imaplib.Time2Internaldate(aware) == '"02-Jan-2024 03:04:05 +0000"'


def test_imap_internaldate_returns_none_for_absent_or_malformed_field():
    assert imaplib.Internaldate2tuple(b"* 1 FETCH (FLAGS (\\Seen))") is None
    assert imaplib.Internaldate2tuple(b'* 1 FETCH (INTERNALDATE "broken")') is None


def test_imap_exception_hierarchy_distinguishes_reconnect_and_readonly_cases():
    assert issubclass(imaplib.IMAP4.abort, imaplib.IMAP4.error)
    assert issubclass(imaplib.IMAP4.readonly, imaplib.IMAP4.error)
    assert imaplib.IMAP4_PORT == 143
    assert imaplib.IMAP4_SSL_PORT == 993
    assert issubclass(imaplib.IMAP4_SSL, imaplib.IMAP4)


class RecordingIMAP(imaplib.IMAP4):
    """保留公开方法的状态与解析，只把真正的线路往返替换成记录。"""

    def __init__(self):
        self.state = "NONAUTH"
        self.commands = []
        self.untagged_responses = {}
        self.select_exists = [b"0"]
        self.is_readonly = False
        self.utf8_enabled = False
        self.literal = None

    def _simple_command(self, name, *args):
        self.commands.append((name, args))
        if name in {"SELECT", "EXAMINE"}:
            self.untagged_responses["EXISTS"] = self.select_exists
        return "OK", [b"completed"]

    def _untagged_response(self, typ, data, name):
        return typ, self.untagged_responses.pop(name, data)


def test_imap_login_always_quotes_password_and_enters_authenticated_state():
    client = RecordingIMAP()

    assert client.login("reader", 'p a"ss\\word') == ("OK", [b"completed"])
    assert client.state == "AUTH"
    assert client.commands == [
        ("LOGIN", ("reader", '"p a\\"ss\\\\word"')),
    ]


def test_imap_login_error_does_not_silently_authenticate():
    client = RecordingIMAP()
    client._simple_command = lambda *args: ("NO", [b"bad credentials"])

    with pytest.raises(imaplib.IMAP4.error, match="bad credentials"):
        client.login("reader", "wrong")


def test_imap_select_and_examine_choose_writable_or_readonly_commands():
    writable = RecordingIMAP()
    writable.state = "AUTH"
    writable.select_exists = [b"12"]

    assert writable.select("Projects") == ("OK", [b"12"])
    assert writable.state == "SELECTED"
    assert writable.commands[-1] == ("SELECT", ("Projects",))

    readonly = RecordingIMAP()
    readonly.state = "AUTH"
    readonly.select_exists = [b"7"]

    assert readonly.select("Archive", readonly=True) == ("OK", [b"7"])
    assert readonly.commands[-1] == ("EXAMINE", ("Archive",))
    assert readonly.is_readonly is True


def test_imap_search_inserts_charset_only_when_requested():
    client = RecordingIMAP()
    client.state = "SELECTED"
    client.untagged_responses["SEARCH"] = [b"2 4 9"]

    assert client.search(None, "UNSEEN") == ("OK", [b"2 4 9"])
    assert client.commands[-1] == ("SEARCH", ("UNSEEN",))

    client.untagged_responses["SEARCH"] = [b"2 4 9"]
    assert client.search("UTF-8", "SUBJECT", '"计划"') == ("OK", [b"2 4 9"])
    assert client.commands[-1] == ("SEARCH", ("CHARSET", "UTF-8", "SUBJECT", '"计划"'))


def test_imap_utf8_accept_forbids_a_search_charset_argument():
    client = RecordingIMAP()
    client.state = "SELECTED"
    client.utf8_enabled = True

    with pytest.raises(imaplib.IMAP4.error, match="charset"):
        client.search("UTF-8", "ALL")


def test_imap_fetch_store_copy_and_expunge_route_to_mandated_untagged_names():
    client = RecordingIMAP()
    client.state = "SELECTED"
    client.untagged_responses.update(
        {
            "FETCH": [(b"2 (UID 9 BODY[] {4}", b"body"), b")"],
            "EXPUNGE": [b"2", b"5"],
        }
    )

    assert client.fetch("2", "(UID BODY[])")[1][0][1] == b"body"
    assert client.store("2", "+FLAGS", r"(\\Seen)")[0] == "OK"
    assert client.copy("2", "Archive") == ("OK", [b"completed"])
    assert client.expunge() == ("OK", [b"2", b"5"])

    assert ("FETCH", ("2", "(UID BODY[])")) in client.commands
    assert ("STORE", ("2", "+FLAGS", r"(\\Seen)")) in client.commands
    assert ("COPY", ("2", "Archive")) in client.commands


def test_imap_uid_prefixes_valid_commands_and_rejects_unknown_ones():
    client = RecordingIMAP()
    client.state = "SELECTED"
    client.untagged_responses["FETCH"] = [b"9 (FLAGS (\\Seen))"]
    client.untagged_responses["SEARCH"] = [b"9 11"]

    assert client.uid("fetch", "9", "(FLAGS)") == (
        "OK",
        [b"9 (FLAGS (\\Seen))"],
    )
    assert client.uid("search", None, "UNSEEN") == ("OK", [b"9 11"])
    assert client.commands[-1] == ("UID", ("SEARCH", None, "UNSEEN"))

    with pytest.raises(imaplib.IMAP4.error, match="Unknown IMAP4 UID command"):
        client.uid("made-up", "1")


def test_imap_append_normalizes_newlines_and_stores_message_as_literal():
    client = RecordingIMAP()
    client.state = "AUTH"
    when = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    result = client.append("INBOX", r"(\\Seen)", when, b"Subject: demo\n\nbody\n")

    assert result == ("OK", [b"completed"])
    assert client.literal == b"Subject: demo\r\n\r\nbody\r\n"
    assert client.commands[-1] == (
        "APPEND",
        ("INBOX", r"(\\Seen)", '"02-Jan-2024 03:04:05 +0000"'),
    )


def test_imap_response_consumes_saved_untagged_data_and_recent_can_poll():
    client = RecordingIMAP()
    client.untagged_responses = {"UIDNEXT": [b"42"], "RECENT": [b"3"]}

    # response 用大写 key 查找缓存，但返回元组保留调用方传入的名称大小写。
    assert client.response("uidnext") == ("uidnext", [b"42"])
    assert "UIDNEXT" not in client.untagged_responses
    assert client.recent() == ("OK", [b"3"])


def test_imap_context_manager_logs_out_even_when_block_raises():
    class LifecycleIMAP(RecordingIMAP):
        def __init__(self):
            super().__init__()
            self.logout_calls = 0

        def logout(self):
            self.logout_calls += 1
            self.state = "LOGOUT"
            return "BYE", [b"logged out"]

    client = LifecycleIMAP()

    with pytest.raises(RuntimeError, match="lesson"):
        with client as entered:
            assert entered is client
            raise RuntimeError("lesson")

    assert client.logout_calls == 1


def test_nntp_exception_hierarchy_preserves_server_response_for_diagnostics():
    error = nntplib.NNTPTemporaryError("400 service temporarily unavailable")

    assert isinstance(error, nntplib.NNTPError)
    assert error.response == "400 service temporarily unavailable"
    assert issubclass(nntplib.NNTPReplyError, nntplib.NNTPError)
    assert issubclass(nntplib.NNTPPermanentError, nntplib.NNTPError)
    assert issubclass(nntplib.NNTPProtocolError, nntplib.NNTPError)
    assert issubclass(nntplib.NNTPDataError, nntplib.NNTPError)


def test_nntp_decode_header_joins_encoded_words_and_plain_text():
    encoded = "=?utf-8?b?5rWL6K+V?= <reader@example.test>"

    assert nntplib.decode_header(encoded) == "测试 <reader@example.test>"


def test_nntp_namedtuples_expose_both_fields_and_tuple_protocol():
    group = nntplib.GroupInfo("comp.lang.python", "20", "1", "y")
    article = nntplib.ArticleInfo(7, "<id@example.test>", [b"body"])

    assert group.group == "comp.lang.python"
    assert tuple(group) == ("comp.lang.python", "20", "1", "y")
    assert article.number == 7
    assert article.lines == [b"body"]


class RecordingNNTP(nntplib.NNTP):
    """公开方法继续解析真实格式，线路层只返回确定的内存响应。"""

    def __init__(self):
        self.encoding = "utf-8"
        self.errors = "surrogateescape"
        self.commands = []
        self.put_lines = []
        self.file = BytesIO()
        self.closed = False
        self._caps = {"VERSION": ["2"], "OVER": []}
        self._cachedoverviewfmt = nntplib._DEFAULT_OVERVIEW_FMT[:]

    def _shortcmd(self, command):
        self.commands.append(command)
        responses = {
            "GROUP Comp.Lang.Python": "211 20 1 20 comp.lang.python",
            "STAT 7": "223 7 <seven@example.test>",
            "NEXT": "223 8 <eight@example.test>",
            "LAST": "223 6 <six@example.test>",
            "DATE": "111 20240102030405",
            "POST": "340 send article",
            "QUIT": "205 bye",
        }
        return responses[command]

    def _longcmdstring(self, command, file=None):
        self.commands.append(command)
        responses = {
            "CAPABILITIES": (
                "101 capability list",
                ["VERSION 2", "OVER", "LIST ACTIVE NEWSGROUPS"],
            ),
            "LIST": (
                "215 list follows",
                ["comp.lang.python 20 1 y", "comp.lang.rust 9 2 m"],
            ),
            "HELP": ("100 help follows", ["GROUP name", "ARTICLE number"]),
            "XHDR subject 1-2": (
                "221 headers follow",
                ["1 First subject", "2 Second subject"],
            ),
            "OVER 1-2": (
                "224 overview follows",
                [
                    "1\tFirst\tA <a@example.test>\tTue\t<1@example.test>\t\t100\t4",
                    "2\tSecond\tB <b@example.test>\tWed\t<2@example.test>\t"
                    "<1@example.test>\t120\t5",
                ],
            ),
            "XOVER 1-2": (
                "224 overview follows",
                ["1\tFirst\tA\tTue\t<1@example.test>\t\t100\t4"],
            ),
        }
        return responses[command]

    def _longcmd(self, command, file=None):
        self.commands.append(command)
        response_codes = {"ARTICLE": "220", "HEAD": "221", "BODY": "222"}
        verb = command.split()[0]
        response = f"{response_codes[verb]} 7 <seven@example.test> follows"
        lines = [b"Subject: demo", b"", b"body"]
        if file is not None:
            for line in lines:
                file.write(line + b"\n")
            lines = []
        return response, lines

    def _putline(self, line):
        self.put_lines.append(line)

    def _getresp(self):
        return "240 article received"

    def _close(self):
        self.closed = True


def test_nntp_capabilities_and_group_listing_return_structured_data():
    client = RecordingNNTP()

    assert client.capabilities() == (
        "101 capability list",
        {"VERSION": ["2"], "OVER": [], "LIST": ["ACTIVE", "NEWSGROUPS"]},
    )
    response, groups = client.list()
    assert response == "215 list follows"
    assert groups == [
        nntplib.GroupInfo("comp.lang.python", "20", "1", "y"),
        nntplib.GroupInfo("comp.lang.rust", "9", "2", "m"),
    ]


def test_nntp_group_and_article_cursor_commands_parse_numbers_and_ids():
    client = RecordingNNTP()

    assert client.group("Comp.Lang.Python") == (
        "211 20 1 20 comp.lang.python",
        20,
        1,
        20,
        "comp.lang.python",
    )
    assert client.stat(7)[1:] == (7, "<seven@example.test>")
    assert client.next()[1:] == (8, "<eight@example.test>")
    assert client.last()[1:] == (6, "<six@example.test>")


@pytest.mark.parametrize("method_name", ["article", "head", "body"])
def test_nntp_article_methods_return_article_info_and_support_file_sink(method_name):
    client = RecordingNNTP()
    method = getattr(client, method_name)

    response, info = method(7)
    assert response.startswith(("220", "221", "222"))
    assert info == nntplib.ArticleInfo(
        7,
        "<seven@example.test>",
        [b"Subject: demo", b"", b"body"],
    )

    class Sink:
        def __init__(self):
            self.data = []

        def write(self, data):
            self.data.append(data)

    sink = Sink()
    _, streamed = method(7, file=sink)
    assert streamed.lines == []
    assert b"".join(sink.data).endswith(b"body\n")


def test_nntp_help_and_xhdr_keep_text_but_split_article_number():
    client = RecordingNNTP()

    assert client.help() == (
        "100 help follows",
        ["GROUP name", "ARTICLE number"],
    )
    assert client.xhdr("subject", "1-2") == (
        "221 headers follow",
        [("1", "First subject"), ("2", "Second subject")],
    )


def test_nntp_overview_uses_rfc3977_names_and_numeric_article_number():
    client = RecordingNNTP()

    response, overview = client.over((1, 2))

    assert response == "224 overview follows"
    assert overview[0][0] == 1
    assert overview[0][1]["subject"] == "First"
    assert overview[0][1][":bytes"] == "100"
    assert overview[1][1]["references"] == "<1@example.test>"


def test_nntp_over_falls_back_to_xover_for_legacy_capabilities():
    client = RecordingNNTP()
    client._caps = {"VERSION": ["1"]}

    response, overview = client.over((1, 2))

    assert response == "224 overview follows"
    assert client.commands[-1] == "XOVER 1-2"
    assert overview[0][0] == 1


def test_nntp_date_parses_server_utc_timestamp():
    client = RecordingNNTP()

    response, value = client.date()

    assert response == "111 20240102030405"
    assert value == datetime(2024, 1, 2, 3, 4, 5)


def test_nntp_post_normalizes_lines_dot_stuffs_and_writes_terminator():
    client = RecordingNNTP()

    assert client.post(b"Subject: demo\n\n.leading\nbody\n") == "240 article received"
    assert client.file.getvalue() == (
        b"Subject: demo\r\n\r\n..leading\r\nbody\r\n.\r\n"
    )


def test_nntp_context_manager_quits_and_closes_connection():
    client = RecordingNNTP()

    with client as entered:
        assert entered is client

    assert client.commands[-1] == "QUIT"
    assert client.closed is True
