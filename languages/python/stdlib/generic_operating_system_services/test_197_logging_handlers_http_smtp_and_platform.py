"""197｜HTTP/SMTP handler 的传输适配点与 Windows Event Log hooks。

网络 handler 在 ``emit`` 才建立连接，因此测试用内存 connection/SMTP fake 覆盖完整映射，
不访问网络。生产代码还应考虑超时、凭据和失败降级；这些 handler 会通过 handleError
报告失败而非提供持久重试队列。NTEventLogHandler 则依赖 pywin32 和 Windows registry。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.handlers.HTTPHandler
# polyglot-covers: python.logging.handlers.HTTPHandler.mapLogRecord
# polyglot-covers: python.logging.handlers.HTTPHandler.getConnection
# polyglot-covers: python.logging.handlers.HTTPHandler-POST
# polyglot-covers: python.logging.handlers.HTTPHandler-basic-auth
# polyglot-covers: python.logging.handlers.SMTPHandler
# polyglot-covers: python.logging.handlers.SMTPHandler.getSubject
# polyglot-covers: python.logging.handlers.SMTPHandler-auth-starttls
# polyglot-covers: python.logging.handlers.NTEventLogHandler
# polyglot-covers: python.logging.handlers.NTEventLogHandler-mapping-hooks

import logging
from logging.handlers import HTTPHandler
from logging.handlers import NTEventLogHandler
from logging.handlers import SMTPHandler

import pytest


class FakeHTTPConnection:
    def __init__(self):
        self.request = None
        self.headers = []
        self.body = None
        self.ended = False
        self.response_read = False

    def putrequest(self, method, url):
        self.request = (method, url)

    def putheader(self, name, value):
        self.headers.append((name, value))

    def endheaders(self):
        self.ended = True

    def send(self, body):
        self.body = body

    def getresponse(self):
        self.response_read = True
        return object()


class OfflineHTTPHandler(HTTPHandler):
    def __init__(self, connection, **kwargs):
        self.connection = connection
        super().__init__(**kwargs)

    def getConnection(self, host, secure):
        assert host == "logs.example"
        assert secure is True
        return self.connection


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.endpoint = (host, port, timeout)
        self.calls = []
        self.message = None
        type(self).instances.append(self)

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, *args):
        self.calls.append(("starttls", args))

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, message):
        self.calls.append("send_message")
        self.message = message

    def quit(self):
        self.calls.append("quit")


def _record(level=logging.ERROR, message="payload"):
    return logging.makeLogRecord(
        {
            "name": "polyglot.remote",
            "levelno": level,
            "levelname": logging.getLevelName(level),
            "msg": message,
            "args": (),
        }
    )


def test_http_handler_builds_post_form_and_basic_authorization_without_network():
    """mapLogRecord 返回字段 mapping；POST body 使用 application/x-www-form-urlencoded。"""

    connection = FakeHTTPConnection()
    handler = OfflineHTTPHandler(
        connection,
        host="logs.example",
        url="/events",
        method="post",
        secure=True,
        credentials=("user", "password"),
    )
    record = _record()
    try:
        assert handler.mapLogRecord(record) is record.__dict__
        handler.emit(record)
    finally:
        handler.close()

    headers = dict(connection.headers)
    assert connection.request == ("POST", "/events")
    assert headers["Content-type"] == "application/x-www-form-urlencoded"
    assert headers["Authorization"].startswith("Basic ")
    assert b"msg=payload" in connection.body
    assert connection.ended is True
    assert connection.response_read is True


def test_http_handler_rejects_invalid_method_and_plaintext_tls_context():
    """context 只对 HTTPS 有意义；method 在构造时规范成大写并立即校验。"""

    with pytest.raises(ValueError, match="GET or POST"):
        HTTPHandler("example.invalid", "/", method="DELETE")
    with pytest.raises(ValueError, match="secure=True"):
        HTTPHandler("example.invalid", "/", secure=False, context=object())


def test_smtp_handler_formats_message_and_runs_auth_tls_sequence(monkeypatch):
    """用 fake 替代 smtplib.SMTP；secure=() 仍表示应执行 STARTTLS。"""

    import smtplib

    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    handler = SMTPHandler(
        mailhost=("mail.example", 2525),
        fromaddr="sender@example",
        toaddrs=["first@example", "second@example"],
        subject="Build failed",
        credentials=("user", "password"),
        secure=(),
        timeout=4.0,
    )
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    record = _record()
    try:
        assert handler.getSubject(record) == "Build failed"
        handler.emit(record)
    finally:
        handler.close()

    smtp = FakeSMTP.instances[0]
    assert smtp.endpoint == ("mail.example", 2525, 4.0)
    assert smtp.calls == [
        "ehlo",
        ("starttls", ()),
        "ehlo",
        ("login", "user", "password"),
        "send_message",
        "quit",
    ]
    assert smtp.message["To"] == "first@example,second@example"
    assert smtp.message["Subject"] == "Build failed"
    assert "ERROR:payload" in smtp.message.get_content()


def test_nt_event_log_mapping_hooks_are_pure_but_constructor_is_platform_bound():
    """跳过 pywin32 构造，直接展示可覆盖的 ID/category/type mapping hooks。"""

    handler = object.__new__(NTEventLogHandler)
    handler.typemap = {logging.ERROR: 99}
    handler.deftype = 1
    error = _record(logging.ERROR)
    custom = _record(25)

    assert handler.getMessageID(error) == 1
    assert handler.getEventCategory(error) == 0
    assert handler.getEventType(error) == 99
    assert handler.getEventType(custom) == 1
