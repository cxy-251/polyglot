"""577｜smtplib 邮件提交、ESMTP 能力协商，以及 smtpd 旧式服务端扩展契约。

客户端案例把 SMTP 信封、消息正文和认证/TLS 阶段分开；服务端案例只演示
Python 3.10 仍提供的扩展点，不启动 asyncore 监听器。``smtpd`` 已弃用，
实际新服务应迁移到 asyncio 方案。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.smtplib python.smtplib.SMTP-default-state
# polyglot-covers: python.smtplib.getreply-multiline python.smtplib.ehlo-features
# polyglot-covers: python.smtplib.putcmd-newline-injection python.smtplib.quoteaddr
# polyglot-covers: python.smtplib.quotedata-crlf-dot-stuffing
# polyglot-covers: python.smtplib.exception-hierarchy python.smtplib.response-exception-fields
# polyglot-covers: python.smtplib.sendmail-envelope-vs-headers
# polyglot-covers: python.smtplib.sendmail-partial-recipient-refusal
# polyglot-covers: python.smtplib.sendmail-all-recipients-refused
# polyglot-covers: python.smtplib.sendmail-size-and-options python.smtplib.data-normalization
# polyglot-covers: python.smtplib.send_message-header-envelope python.smtplib.bcc-removal
# polyglot-covers: python.smtplib.send_message-smtputf8-gate
# polyglot-covers: python.smtplib.auth-plain-login-cram-md5 python.smtplib.login-mechanism-order
# polyglot-covers: python.smtplib.starttls-capability-gate python.smtplib.SMTP_SSL-LMTP
# polyglot-covers: python.smtplib.SMTP-context-manager
# polyglot-covers: python.stdlib.smtpd python.smtpd-deprecated-3.6
# polyglot-covers: python.smtpd.SMTPServer.process_message-contract
# polyglot-covers: python.smtpd.DebuggingServer python.smtpd.channel_class
# polyglot-covers: python.smtpd.decode_data-vs-smtputf8 python.smtpd.message-options

from email.message import EmailMessage
from io import BytesIO

import smtplib
import smtpd
import pytest


class MemorySMTPSocket:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


def test_smtp_default_state_and_exception_payloads_are_explicit():
    client = smtplib.SMTP(local_hostname="client.example.test")

    assert client.sock is None
    assert client.does_esmtp is False
    assert client.esmtp_features == {}
    assert issubclass(smtplib.SMTPException, OSError)
    assert issubclass(smtplib.SMTPDataError, smtplib.SMTPResponseException)

    response_error = smtplib.SMTPDataError(554, b"transaction failed")
    assert response_error.smtp_code == 554
    assert response_error.smtp_error == b"transaction failed"

    sender_error = smtplib.SMTPSenderRefused(550, b"blocked", "from@example.test")
    assert sender_error.sender == "from@example.test"


def test_smtp_ehlo_parses_multiline_extensions_and_sends_crlf_command():
    client = smtplib.SMTP(local_hostname="client.example.test")
    client.sock = MemorySMTPSocket()
    client.file = BytesIO(
        b"250-mail.example.test greets client\r\n"
        b"250-SIZE 1048576\r\n"
        b"250-AUTH PLAIN LOGIN\r\n"
        b"250-8BITMIME\r\n"
        b"250 SMTPUTF8\r\n"
    )

    code, message = client.ehlo("client.example.test")

    assert code == 250
    assert b"SIZE 1048576" in message
    assert client.does_esmtp is True
    assert client.esmtp_features == {
        "size": "1048576",
        "auth": " PLAIN LOGIN",
        "8bitmime": "",
        "smtputf8": "",
    }
    assert client.has_extn("SMTPUTF8") is True
    assert client.sock.sent == [b"ehlo client.example.test\r\n"]


def test_smtp_getreply_joins_multiline_text_and_rejects_overlong_line():
    client = smtplib.SMTP(local_hostname="client.example.test")
    client.sock = MemorySMTPSocket()
    client.file = BytesIO(b"250-first\r\n250 second\r\n")

    assert client.getreply() == (250, b"first\nsecond")

    client.file = BytesIO(b"250 " + b"x" * (smtplib._MAXLINE + 1) + b"\r\n")
    with pytest.raises(smtplib.SMTPResponseException) as caught:
        client.getreply()
    assert caught.value.smtp_code == 500


def test_smtp_command_rejects_crlf_injection_before_writing_socket():
    client = smtplib.SMTP(local_hostname="client.example.test")
    client.sock = MemorySMTPSocket()

    with pytest.raises(ValueError, match="newline"):
        client.putcmd("MAIL", "FROM:<safe@example.test>\r\nRCPT TO:<victim@example.test>")

    assert client.sock.sent == []


def test_smtp_address_and_data_quoting_follow_wire_rules():
    assert smtplib.quoteaddr("Display Name <reader@example.test>") == "<reader@example.test>"
    assert smtplib.quoteaddr("reader@example.test") == "<reader@example.test>"

    quoted = smtplib.quotedata("alpha\n.leading\r\nend")
    assert quoted == "alpha\r\n..leading\r\nend"


class WorkflowSMTP(smtplib.SMTP):
    def __init__(self, recipient_responses=None, *, data_response=(250, b"queued")):
        super().__init__(local_hostname="client.example.test")
        self.does_esmtp = True
        self.esmtp_features = {"size": "1048576", "8bitmime": ""}
        self.recipient_responses = recipient_responses or {}
        self.data_response = data_response
        self.calls = []

    def ehlo_or_helo_if_needed(self):
        self.calls.append(("greeting",))

    def mail(self, sender, options=()):
        self.calls.append(("mail", sender, tuple(options)))
        return 250, b"sender ok"

    def rcpt(self, recipient, options=()):
        self.calls.append(("rcpt", recipient, tuple(options)))
        return self.recipient_responses.get(recipient, (250, b"recipient ok"))

    def data(self, message):
        self.calls.append(("data", message))
        return self.data_response

    def rset(self):
        self.calls.append(("rset",))
        return 250, b"reset"


def test_sendmail_returns_only_refused_recipients_and_still_delivers_to_accepted_ones():
    client = WorkflowSMTP(
        {"blocked@example.test": (550, b"mailbox unavailable")}
    )
    message = "From: header@example.test\nTo: header-recipient@example.test\n\nbody"

    refused = client.sendmail(
        "envelope@example.test",
        ["ok@example.test", "blocked@example.test"],
        message,
        mail_options=("8bitmime",),
        rcpt_options=("NOTIFY=FAILURE",),
    )

    assert refused == {"blocked@example.test": (550, b"mailbox unavailable")}
    mail_call = next(call for call in client.calls if call[0] == "mail")
    assert mail_call[1] == "envelope@example.test"
    assert "size=" in " ".join(mail_call[2]).lower()
    assert "8bitmime" in mail_call[2]

    data = next(call[1] for call in client.calls if call[0] == "data")
    assert data.startswith(b"From: header@example.test\r\n")
    # sendmail 的信封参数不会重写 From/To 头；
    # 两层地址必须由调用方有意识地区分。
    assert b"header-recipient@example.test" in data


def test_sendmail_raises_when_every_recipient_is_refused_and_resets_transaction():
    client = WorkflowSMTP(
        {
            "a@example.test": (550, b"no a"),
            "b@example.test": (551, b"no b"),
        }
    )

    with pytest.raises(smtplib.SMTPRecipientsRefused) as caught:
        client.sendmail(
            "sender@example.test",
            ["a@example.test", "b@example.test"],
            b"Subject: demo\r\n\r\nbody",
        )

    assert set(caught.value.recipients) == {"a@example.test", "b@example.test"}
    assert client.calls[-1] == ("rset",)


def test_sendmail_raises_specific_sender_and_data_errors():
    sender_client = WorkflowSMTP()
    sender_client.mail = lambda sender, options=(): (550, b"sender denied")

    with pytest.raises(smtplib.SMTPSenderRefused) as sender_error:
        sender_client.sendmail("bad@example.test", ["ok@example.test"], b"body")
    assert sender_error.value.sender == "bad@example.test"

    data_client = WorkflowSMTP(data_response=(554, b"content rejected"))
    with pytest.raises(smtplib.SMTPDataError) as data_error:
        data_client.sendmail("ok@example.test", ["to@example.test"], b"body")
    assert data_error.value.smtp_code == 554


class MessageCaptureSMTP(smtplib.SMTP):
    def __init__(self, *, smtputf8=True):
        super().__init__(local_hostname="client.example.test")
        self.does_esmtp = True
        self.esmtp_features = {"smtputf8": ""} if smtputf8 else {}
        self.captured = None

    def ehlo_or_helo_if_needed(self):
        return None

    def sendmail(self, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()):
        self.captured = (from_addr, to_addrs, msg, tuple(mail_options), rcpt_options)
        return {}


def test_send_message_derives_envelope_from_headers_and_removes_bcc_copy():
    message = EmailMessage()
    message["From"] = "Sender <sender@example.test>"
    message["To"] = "Primary <to@example.test>"
    message["Cc"] = "copy@example.test"
    message["Bcc"] = "hidden@example.test"
    message["Subject"] = "demo"
    message.set_content("body")
    client = MessageCaptureSMTP()

    assert client.send_message(message) == {}
    from_addr, recipients, serialized, options, _ = client.captured

    assert from_addr == "sender@example.test"
    assert recipients == [
        "to@example.test",
        "hidden@example.test",
        "copy@example.test",
    ]
    assert b"Bcc:" not in serialized
    assert message["Bcc"] == "hidden@example.test"
    assert options == ()


def test_send_message_requires_smtputf8_for_internationalized_envelope():
    message = EmailMessage()
    message["From"] = "发送者 <用户@例子.测试>"
    message["To"] = "reader@example.test"
    message.set_content("正文")
    client = MessageCaptureSMTP(smtputf8=False)

    with pytest.raises(smtplib.SMTPNotSupportedError, match="SMTPUTF8"):
        client.send_message(message)


def test_smtp_auth_helpers_build_plain_login_and_cram_md5_responses():
    client = smtplib.SMTP(local_hostname="client.example.test")
    client.user = "reader"
    client.password = "secret"

    assert client.auth_plain() == "\0reader\0secret"
    assert client.auth_login() == "reader"
    assert client.auth_login(b"Password:") == "secret"

    cram = client.auth_cram_md5(b"<challenge@example.test>")
    user, digest = cram.split()
    assert user == "reader"
    assert len(digest) == 32


def test_smtp_login_tries_server_mechanisms_in_preferred_order():
    class AuthenticationSMTP(smtplib.SMTP):
        def __init__(self):
            super().__init__(local_hostname="client.example.test")
            self.esmtp_features = {"auth": "LOGIN PLAIN CRAM-MD5"}
            self.attempts = []

        def ehlo_or_helo_if_needed(self):
            return None

        def auth(self, mechanism, authobject, *, initial_response_ok=True):
            self.attempts.append((mechanism, initial_response_ok))
            if mechanism == "CRAM-MD5":
                raise smtplib.SMTPAuthenticationError(535, b"try another mechanism")
            return 235, b"authenticated"

    client = AuthenticationSMTP()

    assert client.login("reader", "secret", initial_response_ok=False) == (
        235,
        b"authenticated",
    )
    assert client.attempts == [("CRAM-MD5", False), ("PLAIN", False)]


def test_starttls_requires_advertised_extension_before_touching_ssl():
    client = smtplib.SMTP(local_hostname="client.example.test")
    client.esmtp_features = {}
    client.ehlo_or_helo_if_needed = lambda: None

    with pytest.raises(smtplib.SMTPNotSupportedError, match="STARTTLS"):
        client.starttls()


def test_ssl_lmtp_and_context_manager_have_distinct_transport_roles():
    assert issubclass(smtplib.SMTP_SSL, smtplib.SMTP)
    assert issubclass(smtplib.LMTP, smtplib.SMTP)
    assert smtplib.SMTP_PORT == 25
    assert smtplib.SMTP_SSL_PORT == 465
    assert smtplib.LMTP_PORT == 2003

    class LifecycleSMTP(smtplib.SMTP):
        def __init__(self):
            super().__init__(local_hostname="client.example.test")
            self.sock = object()
            self.commands = []
            self.closed = False

        def docmd(self, command, args=""):
            self.commands.append((command, args))
            return 221, b"bye"

        def close(self):
            self.closed = True
            self.sock = None

    client = LifecycleSMTP()
    with client as entered:
        assert entered is client

    assert client.commands == [("QUIT", "")]
    assert client.closed is True


def test_smtpd_base_server_requires_process_message_override():
    server = smtpd.SMTPServer.__new__(smtpd.SMTPServer)

    with pytest.raises(NotImplementedError):
        server.process_message(
            ("127.0.0.1", 40000),
            "sender@example.test",
            ["reader@example.test"],
            b"Subject: demo\n\nbody",
        )


def test_smtpd_custom_process_message_receives_envelope_data_and_options():
    class CapturingServer(smtpd.SMTPServer):
        def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
            self.captured = (peer, mailfrom, rcpttos, data, kwargs)
            return "451 queued for later"

    server = CapturingServer.__new__(CapturingServer)
    result = server.process_message(
        ("127.0.0.1", 40000),
        "sender@example.test",
        ["reader@example.test"],
        b"Subject: demo\n\nbody",
        mail_options=["BODY=8BITMIME", "SMTPUTF8"],
        rcpt_options=[],
    )

    assert result == "451 queued for later"
    assert server.captured[-1] == {
        "mail_options": ["BODY=8BITMIME", "SMTPUTF8"],
        "rcpt_options": [],
    }


def test_smtpd_debugging_server_prints_and_discards_message(capsys):
    server = smtpd.DebuggingServer.__new__(smtpd.DebuggingServer)
    server._decode_data = False

    result = server.process_message(
        ("127.0.0.1", 40000),
        "sender@example.test",
        ["reader@example.test"],
        b"Subject: demo\n\nbody",
        mail_options=["BODY=8BITMIME"],
        rcpt_options=[],
    )

    output = capsys.readouterr().out
    assert result is None
    assert "MESSAGE FOLLOWS" in output
    assert "Subject: demo" in output
    assert "END MESSAGE" in output


def test_smtpd_class_roles_and_channel_override_are_visible_without_binding_socket():
    class TeachingChannel(smtpd.SMTPChannel):
        pass

    class TeachingServer(smtpd.SMTPServer):
        channel_class = TeachingChannel

    assert issubclass(smtpd.DebuggingServer, smtpd.SMTPServer)
    assert issubclass(smtpd.PureProxy, smtpd.SMTPServer)
    assert issubclass(smtpd.MailmanProxy, smtpd.PureProxy)
    assert TeachingServer.channel_class is TeachingChannel
    assert smtpd.DATA_SIZE_DEFAULT == 33554432


def test_smtpd_utf8_and_decoded_data_modes_are_mutually_exclusive():
    with pytest.raises(ValueError, match="decode_data and enable_SMTPUTF8"):
        smtpd.SMTPServer(
            ("127.0.0.1", 0),
            None,
            map={},
            enable_SMTPUTF8=True,
            decode_data=True,
        )
