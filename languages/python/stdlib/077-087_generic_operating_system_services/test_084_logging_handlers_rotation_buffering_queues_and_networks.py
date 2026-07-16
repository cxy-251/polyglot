"""084｜``logging.handlers`` 文件监视、尺寸轮转与时间轮转。

WatchedFileHandler 通过 device/inode 发现外部轮转，适合 Unix 上由 logrotate 管理的文件。
RotatingFileHandler 在写入前按预计尺寸轮转；TimedRotatingFileHandler 的旧文件清理依赖
可排序 suffix。``namer``/``rotator`` 可定制名字和搬运方式，但必须保持快速、确定。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.logging.handlers.WatchedFileHandler
# polyglot-covers: python.logging.handlers.WatchedFileHandler.reopenIfNeeded
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.namer
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.rotator
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.rotation_filename
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.rotate
# polyglot-covers: python.logging.handlers.RotatingFileHandler
# polyglot-covers: python.logging.handlers.RotatingFileHandler-size-rollover
# polyglot-covers: python.logging.handlers.RotatingFileHandler-backupCount
# polyglot-covers: python.logging.handlers.TimedRotatingFileHandler
# polyglot-covers: python.logging.handlers.TimedRotatingFileHandler.computeRollover
# polyglot-covers: python.logging.handlers.TimedRotatingFileHandler.getFilesToDelete




import logging
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler
from logging.handlers import WatchedFileHandler
import os
import pytest
from logging.handlers import BufferingHandler
from logging.handlers import MemoryHandler
from logging.handlers import QueueHandler
from logging.handlers import QueueListener
import queue
from logging.handlers import DatagramHandler
from logging.handlers import SocketHandler
from logging.handlers import SysLogHandler
import pickle
import struct
from logging.handlers import HTTPHandler
from logging.handlers import NTEventLogHandler
from logging.handlers import SMTPHandler

@pytest.mark.skipif(os.name != "posix", reason="inode-based external rotation is Unix-specific")
def test_watched_file_handler_reopens_after_external_rename(tmp_path):
    """外部工具 move 原文件并创建同名新文件后，下一次 emit 自动切换 inode。"""

    active = tmp_path / "application.log"
    rotated = tmp_path / "application.log.old"
    handler = WatchedFileHandler(active, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("polyglot.case193.watched")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("before rotation")
        os.rename(active, rotated)
        active.write_text("", encoding="utf-8")
        logger.info("after rotation")
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert rotated.read_text(encoding="utf-8") == "before rotation\n"
    assert active.read_text(encoding="utf-8") == "after rotation\n"


def test_rotating_base_callbacks_customize_destination_and_file_move(tmp_path):
    """rotation_filename 调 namer，rotate 调 rotator；callback 自己负责实际搬运。"""

    log_path = tmp_path / "callback.log"
    source = tmp_path / "source.log"
    destination = tmp_path / "destination.log.gz"
    source.write_text("payload", encoding="utf-8")
    moved = []
    handler = RotatingFileHandler(log_path, delay=True)
    handler.namer = lambda default_name: default_name + ".gz"

    def rotator(source_name, destination_name):
        moved.append((source_name, destination_name))
        os.replace(source_name, destination_name)

    handler.rotator = rotator
    try:
        assert handler.rotation_filename("archive.log.1") == "archive.log.1.gz"
        handler.rotate(str(source), str(destination))
    finally:
        handler.close()

    assert moved == [(str(source), str(destination))]
    assert destination.read_text(encoding="utf-8") == "payload"
    assert source.exists() is False


def test_size_rotation_keeps_numbered_backups_newest_first(tmp_path):
    """达到阈值的那条记录写入新文件；``.1`` 始终是最近一次旧 active 文件。"""

    path = tmp_path / "sized.log"
    handler = RotatingFileHandler(
        path,
        mode="a",
        maxBytes=12,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("polyglot.case193.size")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("first")
        logger.info("second")
        logger.info("third")
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert path.read_text(encoding="utf-8") == "third\n"
    assert (tmp_path / "sized.log.1").read_text(encoding="utf-8") == "second\n"
    assert (tmp_path / "sized.log.2").read_text(encoding="utf-8") == "first\n"


def test_timed_rotation_computes_interval_and_deletes_oldest_matching_suffix(tmp_path):
    """清理只识别 handler suffix regex；无关文件不会误删。"""

    path = tmp_path / "timed.log"
    handler = TimedRotatingFileHandler(
        path,
        when="S",
        interval=5,
        backupCount=2,
        utc=True,
        delay=True,
    )
    names = [
        "timed.log.2024-01-01_00-00-00",
        "timed.log.2024-01-01_00-00-05",
        "timed.log.2024-01-01_00-00-10",
    ]
    for name in names:
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "timed.log.notes").write_text("keep", encoding="utf-8")
    try:
        assert handler.computeRollover(100) == 105
        assert handler.getFilesToDelete() == [str(tmp_path / names[0])]
    finally:
        handler.close()


# ``BufferingHandler`` 与 ``MemoryHandler`` 的 flush 契约。
#
# BufferingHandler 到达 capacity 时调用可覆盖的 ``flush``；基类实现仅清空 buffer。
# MemoryHandler 则把已缓存 record 依次交给 target，可由容量或 ``flushLevel`` 触发。
# 它直接调用 target.handle，因此 target.level 不会像 Logger.callHandlers 中那样自动检查。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.logging.handlers.BufferingHandler
# polyglot-covers: python.logging.handlers.BufferingHandler.capacity
# polyglot-covers: python.logging.handlers.BufferingHandler.shouldFlush
# polyglot-covers: python.logging.handlers.BufferingHandler.flush
# polyglot-covers: python.logging.handlers.MemoryHandler
# polyglot-covers: python.logging.handlers.MemoryHandler.flushLevel
# polyglot-covers: python.logging.handlers.MemoryHandler.target
# polyglot-covers: python.logging.handlers.MemoryHandler.setTarget
# polyglot-covers: python.logging.handlers.MemoryHandler.flushOnClose
# polyglot-covers: python.logging.handlers.MemoryHandler-target-level-not-checked



class BufferCollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def _buffer_record(level, message):
    return logging.makeLogRecord(
        {
            "name": "polyglot.buffer",
            "levelno": level,
            "levelname": logging.getLevelName(level),
            "msg": message,
            "args": (),
        }
    )


def test_base_buffering_handler_flushes_by_capacity_and_clears_records():
    """第二条达到 capacity=2 后同步 flush，基类不会转发这些 record。"""

    handler = BufferingHandler(capacity=2)
    first = _buffer_record(logging.INFO, "first")
    second = _buffer_record(logging.INFO, "second")

    assert handler.shouldFlush(first) is False
    handler.handle(first)
    assert handler.buffer == [first]
    handler.handle(second)
    assert handler.buffer == []
    handler.close()


def test_memory_handler_flush_level_forwards_the_whole_buffer_in_order():
    """ERROR 不只发送自己；它会把此前 INFO/WARNING 一起按原顺序交给 target。"""

    target = BufferCollectingHandler()
    memory = MemoryHandler(
        capacity=10,
        flushLevel=logging.ERROR,
        target=target,
        flushOnClose=False,
    )
    try:
        memory.handle(_buffer_record(logging.INFO, "info"))
        memory.handle(_buffer_record(logging.WARNING, "warning"))
        assert [record.getMessage() for record in memory.buffer] == ["info", "warning"]

        memory.handle(_buffer_record(logging.ERROR, "error"))
        assert memory.buffer == []
        assert [record.getMessage() for record in target.records] == [
            "info",
            "warning",
            "error",
        ]
    finally:
        memory.close()
        target.close()


def test_memory_target_level_is_not_automatically_checked_during_flush():
    """target.handle 跳过 level gate；需要 level 筛选时应在 target 加 filter 或自行 flush。"""

    target = BufferCollectingHandler()
    target.setLevel(logging.CRITICAL)
    memory = MemoryHandler(
        capacity=1,
        target=target,
        flushOnClose=False,
    )
    try:
        memory.handle(_buffer_record(logging.INFO, "still forwarded"))
        assert [record.getMessage() for record in target.records] == ["still forwarded"]
    finally:
        memory.close()
        target.close()


def test_set_target_and_flush_on_close_control_final_delivery():
    """flushOnClose=False 可在异常收尾时丢弃尾部 buffer；True 保持兼容的发送行为。"""

    delivered = BufferCollectingHandler()
    discarded = BufferCollectingHandler()
    flushing = MemoryHandler(capacity=10, target=None, flushOnClose=True)
    non_flushing = MemoryHandler(
        capacity=10,
        target=discarded,
        flushOnClose=False,
    )

    flushing.setTarget(delivered)
    flushing.handle(_buffer_record(logging.INFO, "deliver on close"))
    non_flushing.handle(_buffer_record(logging.INFO, "discard on close"))
    flushing.close()
    non_flushing.close()

    assert [record.getMessage() for record in delivered.records] == [
        "deliver on close"
    ]
    assert discarded.records == []
    delivered.close()
    discarded.close()


# ``QueueHandler``/``QueueListener`` 的 record preparation 与线程管线。
#
# QueueHandler 在生产线程中先 format，再复制 record 并清除难以 pickle 的字段；原 record
# 不会被污染。QueueListener 在后台线程依次派发，``stop`` 写 sentinel 并 join，所以无需
# sleep 也能确定此前的 FIFO record 已处理。是否检查目标 handler.level 由参数显式控制。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.logging.handlers.QueueHandler
# polyglot-covers: python.logging.handlers.QueueHandler.prepare
# polyglot-covers: python.logging.handlers.QueueHandler.enqueue
# polyglot-covers: python.logging.handlers.QueueHandler.put-nowait
# polyglot-covers: python.logging.handlers.QueueHandler-record-copy
# polyglot-covers: python.logging.handlers.QueueListener
# polyglot-covers: python.logging.handlers.QueueListener.start
# polyglot-covers: python.logging.handlers.QueueListener.stop
# polyglot-covers: python.logging.handlers.QueueListener.enqueue_sentinel
# polyglot-covers: python.logging.handlers.QueueListener.prepare
# polyglot-covers: python.logging.handlers.QueueListener-respect-handler-level



class QueueCollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class DisplayValue:
    def __str__(self):
        return "VALUE"


def _queue_record(level, message, args=()):
    return logging.makeLogRecord(
        {
            "name": "polyglot.queue",
            "levelno": level,
            "levelname": logging.getLevelName(level),
            "msg": message,
            "args": args,
        }
    )


def test_queue_prepare_formats_a_copy_and_removes_transport_hostile_fields():
    """consumer 默认不能重新选择 exception formatter，因为 exc_info/exc_text 已清除。"""

    event_queue = queue.Queue()
    handler = QueueHandler(event_queue)
    original = _queue_record(logging.INFO, "value=%s", (DisplayValue(),))

    prepared = handler.prepare(original)

    assert prepared is not original
    assert prepared.message == "value=VALUE"
    assert prepared.msg == "value=VALUE"
    assert prepared.args is None
    assert prepared.exc_info is None
    assert prepared.exc_text is None
    assert prepared.stack_info is None
    assert original.msg == "value=%s"
    assert isinstance(original.args[0], DisplayValue)
    handler.close()


def test_enqueue_uses_non_blocking_queue_protocol():
    """enqueue 本身不 prepare；emit 才组合 prepare + enqueue。"""

    event_queue = queue.Queue(maxsize=1)
    handler = QueueHandler(event_queue)
    record = _queue_record(logging.INFO, "direct")

    handler.enqueue(record)

    assert event_queue.get_nowait() is record
    handler.close()


def test_listener_stop_waits_for_fifo_records_and_respects_handler_levels():
    """stop 的 sentinel 排在既有事件后，join 返回时这些事件已完成派发。"""

    event_queue = queue.Queue()
    producer = QueueHandler(event_queue)
    warning_target = QueueCollectingHandler()
    error_target = QueueCollectingHandler()
    warning_target.setLevel(logging.WARNING)
    error_target.setLevel(logging.ERROR)
    listener = QueueListener(
        event_queue,
        warning_target,
        error_target,
        respect_handler_level=True,
    )
    logger = logging.getLogger("polyglot.case195.pipeline")
    logger.handlers.clear()
    logger.addHandler(producer)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        listener.start()
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        listener.stop()

        assert [record.getMessage() for record in warning_target.records] == [
            "warning",
            "error",
        ]
        assert [record.getMessage() for record in error_target.records] == ["error"]
        assert listener._thread is None
    finally:
        if listener._thread is not None:
            listener.stop()
        logger.removeHandler(producer)
        producer.close()
        warning_target.close()
        error_target.close()


def test_listener_without_level_respect_offers_every_record_to_every_handler():
    """默认兼容行为绕过 handler.level，因为内部直接调用 handler.handle。"""

    target = QueueCollectingHandler()
    target.setLevel(logging.CRITICAL)
    listener = QueueListener(queue.Queue(), target, respect_handler_level=False)
    record = _queue_record(logging.INFO, "offered")

    assert listener.prepare(record) is record
    listener.handle(record)
    assert target.records == [record]
    target.close()


# Socket/Datagram handler 的 wire record 与 SysLog priority 映射。
#
# SocketHandler 发送的是四字节大端长度加 pickle record 字典，而不是文本 formatter 输出；
# 接收端应校验来源，因为 pickle 不能用于不可信数据。这里仅调用离线 ``makePickle``，
# 不创建连接。SysLog 的 facility/priority 组合也可在不打开 socket 时验证。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.logging.handlers.SocketHandler
# polyglot-covers: python.logging.handlers.SocketHandler.makePickle
# polyglot-covers: python.logging.handlers.SocketHandler-length-prefix
# polyglot-covers: python.logging.handlers.SocketHandler-pickle-security
# polyglot-covers: python.logging.handlers.DatagramHandler
# polyglot-covers: python.logging.handlers.DatagramHandler-wire-format
# polyglot-covers: python.logging.handlers.SysLogHandler
# polyglot-covers: python.logging.handlers.SysLogHandler.encodePriority
# polyglot-covers: python.logging.handlers.SysLogHandler.mapPriority
# polyglot-covers: python.logging.handlers.syslog-custom-level-fallback




def _network_record():
    return logging.makeLogRecord(
        {
            "name": "polyglot.transport",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "job=%s",
            "args": (7,),
            "exc_info": None,
        }
    )


@pytest.mark.parametrize(
    "handler_class",
    [SocketHandler, DatagramHandler],
)
def test_socket_family_pickle_has_length_prefix_and_merged_message(handler_class):
    """constructor 只保存 endpoint；不调用 emit/createSocket 就不会进行网络 I/O。"""

    handler = handler_class("example.invalid", 9020)
    try:
        payload = handler.makePickle(_network_record())
    finally:
        handler.close()

    declared_length = struct.unpack(">L", payload[:4])[0]
    record_dict = pickle.loads(payload[4:])

    assert declared_length == len(payload) - 4
    assert record_dict["name"] == "polyglot.transport"
    assert record_dict["msg"] == "job=7"
    assert record_dict["args"] is None
    assert record_dict["exc_info"] is None


def test_syslog_priority_combines_facility_and_severity_numbers_offline():
    """priority = facility * 8 + severity；字符串名称经标准映射后再组合。"""

    handler = object.__new__(SysLogHandler)

    expected = (SysLogHandler.LOG_LOCAL0 << 3) | SysLogHandler.LOG_INFO
    assert handler.encodePriority("local0", "info") == expected
    assert handler.encodePriority(SysLogHandler.LOG_USER, SysLogHandler.LOG_ERR) == 11
    with pytest.raises(KeyError, match="missing"):
        handler.encodePriority("missing", "info")


def test_syslog_level_mapping_falls_back_to_warning_for_custom_names():
    """未知 level name 默认映射 warning；自定义 level 应覆盖 mapPriority 才精确。"""

    handler = object.__new__(SysLogHandler)

    assert handler.mapPriority("DEBUG") == "debug"
    assert handler.mapPriority("CRITICAL") == "critical"
    assert handler.mapPriority("NOTICE") == "warning"


# HTTP/SMTP handler 的传输适配点与 Windows Event Log hooks。
#
# 网络 handler 在 ``emit`` 才建立连接，因此测试用内存 connection/SMTP fake 覆盖完整映射，
# 不访问网络。生产代码还应考虑超时、凭据和失败降级；这些 handler 会通过 handleError
# 报告失败而非提供持久重试队列。NTEventLogHandler 则依赖 pywin32 和 Windows registry。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


def _platform_record(level=logging.ERROR, message="payload"):
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
    record = _platform_record()
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
    record = _platform_record()
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
    assert smtp.message["To"] == "first@example, second@example"
    assert smtp.message["Subject"] == "Build failed"
    assert "ERROR:payload" in smtp.message.get_content()


def test_nt_event_log_mapping_hooks_are_pure_but_constructor_is_platform_bound():
    """跳过 pywin32 构造，直接展示可覆盖的 ID/category/type mapping hooks。"""

    handler = object.__new__(NTEventLogHandler)
    handler.typemap = {logging.ERROR: 99}
    handler.deftype = 1
    error = _platform_record(logging.ERROR)
    custom = _platform_record(25)

    assert handler.getMessageID(error) == 1
    assert handler.getEventCategory(error) == 0
    assert handler.getEventType(error) == 99
    assert handler.getEventType(custom) == 1
