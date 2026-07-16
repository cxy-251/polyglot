"""129｜ftplib 与 poplib 的命令状态机、传输回调、响应解析和安全连接边界。

两个模块都是同步的文本协议客户端。案例不连接公网，而是使用内存
socket、响应脚本和子类覆盖传输钩子。案例保留核心协议语义。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.ftplib python.ftplib.FTP-constructor-defaults
# polyglot-covers: python.ftplib.response-classification python.ftplib.multiline-response
# polyglot-covers: python.ftplib.login-anonymous python.ftplib.login-pass-account-state-machine
# polyglot-covers: python.ftplib.sendcmd python.ftplib.voidcmd python.ftplib.all_errors
# polyglot-covers: python.ftplib.retrbinary python.ftplib.retrlines
# polyglot-covers: python.ftplib.storbinary python.ftplib.storlines
# polyglot-covers: python.ftplib.transfer-callback python.ftplib.crlf-normalization
# polyglot-covers: python.ftplib.mlsd python.ftplib.nlst python.ftplib.dir
# polyglot-covers: python.ftplib.rename-delete-cwd-mkd-pwd-rmd-size
# polyglot-covers: python.ftplib.FTP-context-manager python.ftplib.quit-vs-close
# polyglot-covers: python.ftplib.FTP_TLS python.ftplib.FTP_TLS.prot_p-prot_c
# polyglot-covers: python.stdlib.poplib python.poplib.POP3-response-lines
# polyglot-covers: python.poplib.error_proto python.poplib.dot-unstuffing
# polyglot-covers: python.poplib.user-pass-stat-list-retr-dele-noop-rset-quit
# polyglot-covers: python.poplib.top-uidl-capa python.poplib.apop
# polyglot-covers: python.poplib.stls-capability-gate python.poplib.POP3_SSL
# polyglot-covers: python.poplib.timeout-zero-rejected python.poplib.explicit-quit-3.10

from hashlib import md5
from io import BytesIO, StringIO
from socket import timeout as SocketTimeout

import ftplib
import poplib
import pytest


class ReplyFTP(ftplib.FTP):
    """只替换控制连接响应，仍让 login 等公开方法执行自己的状态机。"""

    def __init__(self, replies):
        super().__init__()
        self.replies = iter(replies)
        self.commands = []

    def sendcmd(self, command):
        self.commands.append(command)
        return next(self.replies)


class MemoryDataSocket:
    def __init__(self, incoming=b"", text=""):
        self.incoming = BytesIO(incoming)
        self.text = text
        self.sent = []
        self.shutdown_calls = []
        self.closed = False

    def recv(self, blocksize):
        return self.incoming.read(blocksize)

    def sendall(self, data):
        self.sent.append(data)

    def makefile(self, mode, encoding=None):
        assert mode == "r"
        return StringIO(self.text)

    def shutdown(self, how):
        self.shutdown_calls.append(how)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


class TransferFTP(ftplib.FTP):
    def __init__(self, data_socket):
        super().__init__()
        self.data_socket = data_socket
        self.transfer_calls = []
        self.commands = []
        self.void_responses = 0

    def voidcmd(self, command):
        # 传输方法会先在控制连接切换 TYPE；内存替身也必须覆盖这一公开状态机步骤。
        self.commands.append(command)
        return "200 type set"

    def sendcmd(self, command):
        # retrlines 使用 sendcmd(TYPE A)，而 binary/upload 路径使用 voidcmd。
        self.commands.append(command)
        return "200 type set"

    def transfercmd(self, command, rest=None):
        self.transfer_calls.append((command, rest))
        return self.data_socket

    def voidresp(self):
        self.void_responses += 1
        return "226 transfer complete"


def test_ftp_defaults_and_protocol_error_hierarchy_are_searchable_without_connecting():
    client = ftplib.FTP()

    assert client.encoding == "utf-8"
    assert client.passiveserver is True
    assert client.sock is None
    assert issubclass(ftplib.error_temp, ftplib.Error)
    assert issubclass(ftplib.error_perm, ftplib.Error)
    assert issubclass(ftplib.error_reply, ftplib.Error)
    assert issubclass(ftplib.error_proto, ftplib.Error)
    assert OSError in ftplib.all_errors
    assert EOFError in ftplib.all_errors


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("150 opening data connection", "150 opening data connection"),
        ("226 transfer complete", "226 transfer complete"),
        ("331 password required", "331 password required"),
    ],
)
def test_ftp_getresp_accepts_preliminary_success_and_intermediate_responses(response, expected):
    client = ftplib.FTP()
    client.getmultiline = lambda: response

    assert client.getresp() == expected


@pytest.mark.parametrize(
    ("response", "exception"),
    [
        ("421 service unavailable", ftplib.error_temp),
        ("550 permission denied", ftplib.error_perm),
        ("699 unexpected numeric class", ftplib.error_proto),
        ("not an FTP response", ftplib.error_proto),
    ],
)
def test_ftp_getresp_maps_status_classes_to_specific_exceptions(response, exception):
    client = ftplib.FTP()
    client.getmultiline = lambda: response

    with pytest.raises(exception, match=response):
        client.getresp()


def test_ftp_multiline_response_ends_only_at_matching_code_and_separator():
    client = ftplib.FTP()
    lines = iter(
        [
            "220-Welcome\n",
            "220-this numeric prefix is still part of the body\n",
            "plain explanatory line\n",
            "220 Ready\n",
        ]
    )
    client.getline = lambda: next(lines).rstrip("\n")

    assert client.getmultiline().splitlines() == [
        "220-Welcome",
        "220-this numeric prefix is still part of the body",
        "plain explanatory line",
        "220 Ready",
    ]


def test_ftp_login_uses_anonymous_default_and_follows_3xx_challenges():
    anonymous = ReplyFTP(["230 logged in"])
    assert anonymous.login() == "230 logged in"
    assert anonymous.commands == ["USER anonymous"]

    challenged = ReplyFTP(
        ["331 password required", "332 account required", "230 logged in"]
    )
    assert challenged.login("reader", "secret", "billing") == "230 logged in"
    assert challenged.commands == ["USER reader", "PASS secret", "ACCT billing"]


def test_ftp_binary_download_streams_blocks_and_preserves_restart_offset():
    socket = MemoryDataSocket(incoming=b"abcdefgh")
    client = TransferFTP(socket)
    blocks = []

    response = client.retrbinary("RETR report.bin", blocks.append, blocksize=3, rest=5)

    assert response == "226 transfer complete"
    assert blocks == [b"abc", b"def", b"gh"]
    assert client.transfer_calls == [("RETR report.bin", 5)]
    assert client.void_responses == 1
    assert socket.closed is True


def test_ftp_text_download_decodes_and_removes_protocol_line_endings():
    socket = MemoryDataSocket(text="alpha\r\nbeta\r\n")
    client = TransferFTP(socket)
    lines = []

    response = client.retrlines("LIST", lines.append)

    assert response == "226 transfer complete"
    assert lines == ["alpha", "beta"]
    assert socket.closed is True


def test_ftp_binary_upload_reads_blocks_calls_progress_and_closes_data_socket():
    socket = MemoryDataSocket()
    client = TransferFTP(socket)
    uploaded = []

    response = client.storbinary(
        "STOR payload.bin",
        BytesIO(b"abcdefgh"),
        blocksize=3,
        callback=uploaded.append,
        rest=2,
    )

    assert response == "226 transfer complete"
    assert socket.sent == [b"abc", b"def", b"gh"]
    assert uploaded == socket.sent
    assert client.transfer_calls == [("STOR payload.bin", 2)]
    # 3.10 不额外 shutdown(SHUT_WR)，而是由 data socket 上下文管理器直接关闭来表达 EOF；
    # 这仍不会关闭 FTP 控制连接。
    assert socket.shutdown_calls == []
    assert socket.closed is True


def test_ftp_text_upload_normalizes_lf_but_does_not_duplicate_existing_crlf():
    socket = MemoryDataSocket()
    client = TransferFTP(socket)
    uploaded = []

    response = client.storlines(
        "STOR notes.txt",
        BytesIO(b"alpha\nbeta\r\ngamma"),
        callback=uploaded.append,
    )

    assert response == "226 transfer complete"
    assert socket.sent == [b"alpha\r\n", b"beta\r\n", b"gamma\r\n"]
    assert uploaded == socket.sent


def test_ftp_mlsd_converts_facts_to_lowercase_dictionary_and_is_lazy():
    class ListingFTP(ftplib.FTP):
        def __init__(self):
            super().__init__()
            self.calls = []

        def retrlines(self, command, callback):
            self.calls.append(command)
            callback("type=file;size=12;Modify=20240101000000; report.txt")
            callback("type=dir;perm=el; archive")
            return "226 listed"

        def sendcmd(self, command):
            self.calls.append(command)
            return "200 options accepted"

    client = ListingFTP()
    listing = client.mlsd("/reports", facts=["type", "size"])

    assert client.calls == []
    assert list(listing) == [
        (
            "report.txt",
            {"type": "file", "size": "12", "modify": "20240101000000"},
        ),
        ("archive", {"type": "dir", "perm": "el"}),
    ]
    assert client.calls == ["OPTS MLST type;size;", "MLSD /reports"]


def test_ftp_nlst_returns_names_while_dir_accepts_a_listing_callback():
    class ConvenienceFTP(ftplib.FTP):
        def __init__(self):
            super().__init__()
            self.commands = []

        def retrlines(self, command, callback):
            self.commands.append(command)
            callback("alpha.txt")
            callback("archive")
            return "226 listed"

    client = ConvenienceFTP()
    directory_lines = []

    assert client.nlst("/reports") == ["alpha.txt", "archive"]
    assert client.dir("/reports", directory_lines.append) is None
    assert directory_lines == ["alpha.txt", "archive"]
    assert client.commands == ["NLST /reports", "LIST /reports"]


def test_ftp_convenience_methods_build_commands_and_parse_size():
    class CommandFTP(ftplib.FTP):
        def __init__(self):
            super().__init__()
            self.sent = []

        def voidcmd(self, command):
            self.sent.append(command)
            responses = {
                "CWD reports": "250 directory changed",
                "PWD": '257 "/srv/data" is current directory',
                "MKD reports": '257 "/srv/data/reports" created',
                "RMD archive": "250 removed",
                "RNTO new.txt": "250 renamed",
            }
            return responses[command]

        def sendcmd(self, command):
            self.sent.append(command)
            responses = {
                "SIZE payload.bin": "213 4096",
                "RNFR old.txt": "350 ready for destination",
                "DELE old.bin": "250 deleted",
            }
            return responses[command]

    client = CommandFTP()

    assert client.cwd("reports") == "250 directory changed"
    assert client.pwd() == "/srv/data"
    assert client.mkd("reports") == "/srv/data/reports"
    assert client.size("payload.bin") == 4096
    assert client.rename("old.txt", "new.txt") == "250 renamed"
    assert client.delete("old.bin") == "250 deleted"
    assert client.rmd("archive") == "250 removed"


def test_ftp_context_manager_returns_client_and_performs_polite_quit():
    class LifecycleFTP(ftplib.FTP):
        def __init__(self):
            super().__init__()
            self.sock = object()
            self.quit_calls = 0

        def quit(self):
            self.quit_calls += 1
            self.sock = None
            return "221 bye"

    client = LifecycleFTP()

    with client as entered:
        assert entered is client

    assert client.quit_calls == 1


def test_ftp_tls_data_protection_is_explicit_and_reversible():
    client = ftplib.FTP_TLS()
    commands = []
    client.voidcmd = lambda command: commands.append(command) or "200 ok"

    assert client.prot_p() == "200 ok"
    assert client._prot_p is True
    assert commands == ["PBSZ 0", "PROT P"]

    assert client.prot_c() == "200 ok"
    assert client._prot_p is False
    assert commands[-1] == "PROT C"


class RecordingPOP3(poplib.POP3):
    """绕过构造连接，只记录公开命令选择了短响应还是多行响应。"""

    def __init__(self):
        self.encoding = "UTF-8"
        self.welcome = b"+OK <stamp@example.test> ready"
        self._debugging = 0
        self._tls_established = False
        self.short = []
        self.long = []
        self.closed = False

    def _shortcmd(self, command):
        self.short.append(command)
        responses = {
            "STAT": b"+OK 2 120",
            "LIST 1": b"+OK 1 50",
            "UIDL 1": b"+OK 1 abc",
        }
        return responses.get(command, b"+OK")

    def _longcmd(self, command):
        self.long.append(command)
        responses = {
            "LIST": (b"+OK", [b"1 50", b"2 70"], 12),
            "RETR 1": (b"+OK", [b"Subject: demo", b"", b"body"], 22),
            "TOP 1 5": (b"+OK", [b"Subject: demo", b"", b"body"], 22),
            "UIDL": (b"+OK", [b"1 abc", b"2 def"], 14),
            "CAPA": (b"+OK", [b"USER", b"SASL PLAIN LOGIN", b"STLS"], 26),
        }
        return responses[command]

    def close(self):
        self.closed = True


def test_pop3_line_parser_strips_crlf_and_reports_original_octet_count():
    client = poplib.POP3.__new__(poplib.POP3)
    client.file = BytesIO(b"+OK ready\r\n")
    client._debugging = 0

    assert client._getline() == (b"+OK ready", 11)


def test_pop3_short_response_rejects_err_and_accepts_ok():
    client = poplib.POP3.__new__(poplib.POP3)
    client.file = BytesIO(b"+OK welcome\r\n-ERR denied\r\n")
    client._debugging = 0

    assert client._getresp() == b"+OK welcome"
    with pytest.raises(poplib.error_proto, match="denied"):
        client._getresp()


def test_pop3_long_response_removes_dot_stuffing_and_excludes_terminator():
    client = poplib.POP3.__new__(poplib.POP3)
    client.file = BytesIO(b"+OK follows\r\nalpha\r\n..leading-dot\r\n.\r\n")
    client._debugging = 0

    response, lines, octets = client._getlongresp()

    assert response == b"+OK follows"
    assert lines == [b"alpha", b".leading-dot"]
    # 返回 octets 按去掉 dot-stuffing 后的逻辑响应行计数，并保留每行协议 CRLF。
    assert octets == len(b"alpha\r\n.leading-dot\r\n")


def test_pop3_public_commands_select_short_or_multiline_protocol_forms():
    client = RecordingPOP3()

    assert client.user("reader") == b"+OK"
    assert client.pass_("secret") == b"+OK"
    assert client.stat() == (2, 120)
    assert client.list(1) == b"+OK 1 50"
    assert client.list() == (b"+OK", [b"1 50", b"2 70"], 12)
    assert client.retr(1)[1][-1] == b"body"
    assert client.top(1, 5)[1][0] == b"Subject: demo"
    assert client.uidl(1) == b"+OK 1 abc"
    assert client.uidl()[1] == [b"1 abc", b"2 def"]
    assert client.dele(1) == b"+OK"
    assert client.noop() == b"+OK"
    assert client.rset() == b"+OK"
    assert client.quit() == b"+OK"

    assert "USER reader" in client.short
    assert "RETR 1" in client.long


def test_pop3_310_requires_explicit_quit_and_closes_protocol_state():
    client = RecordingPOP3()

    assert not hasattr(client, "__enter__")
    try:
        assert client.noop() == b"+OK"
    finally:
        client.quit()

    assert client.short[-1] == "QUIT"
    assert client.closed is True


def test_pop3_capa_maps_each_capability_to_zero_or_more_arguments():
    client = RecordingPOP3()

    assert client.capa() == {
        "USER": [],
        "SASL": ["PLAIN", "LOGIN"],
        "STLS": [],
    }


def test_pop3_apop_uses_md5_of_server_challenge_plus_password():
    client = RecordingPOP3()
    expected = md5(b"<stamp@example.test>secret").hexdigest()

    assert client.apop("reader", "secret") == b"+OK"
    assert client.short[-1] == f"APOP reader {expected}"


def test_pop3_apop_requires_a_timestamp_challenge():
    client = RecordingPOP3()
    client.welcome = b"+OK no challenge"

    with pytest.raises(poplib.error_proto, match="APOP not supported"):
        client.apop("reader", "secret")


def test_pop3_stls_checks_capability_before_touching_tls_or_socket():
    client = RecordingPOP3()
    client.capa = lambda: {"USER": []}

    with pytest.raises(poplib.error_proto, match="STLS"):
        client.stls()


def test_pop3_constructor_passes_timeout_to_socket_and_rejects_zero(monkeypatch):
    def reject_connection(address, timeout, source_address=None):
        assert address == ("mail.example.test", poplib.POP3_PORT)
        assert timeout == 0
        raise ValueError("Non-blocking socket (timeout=0) is not supported")

    monkeypatch.setattr(poplib.socket, "create_connection", reject_connection)

    with pytest.raises(ValueError, match="Non-blocking"):
        poplib.POP3("mail.example.test", timeout=0)


def test_pop3_ssl_is_protocol_subclass_and_socket_timeout_remains_connection_error():
    assert issubclass(poplib.POP3_SSL, poplib.POP3)
    assert poplib.POP3_PORT == 110
    assert poplib.POP3_SSL_PORT == 995
    assert issubclass(SocketTimeout, OSError)
