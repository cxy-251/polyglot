"""188｜核心 ``Handler``、``StreamHandler``、``FileHandler`` 与 ``NullHandler``。

logger 决定是否创建 record，handler 再执行自己的 level/filter、format 和 I/O。
StreamHandler 的目标只需提供 ``write``/``flush``；FileHandler 的 ``delay=True`` 可把
打开文件推迟到首次 emit。库代码应安装 NullHandler，而不是擅自配置应用 root logger。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.Handler python.logging.Handler.emit
# polyglot-covers: python.logging.Handler.setLevel python.logging.Handler.setFormatter
# polyglot-covers: python.logging.Handler.handle python.logging.Handler.filter
# polyglot-covers: python.logging.StreamHandler python.logging.StreamHandler.terminator
# polyglot-covers: python.logging.StreamHandler.setStream
# polyglot-covers: python.logging.StreamHandler.flush
# polyglot-covers: python.logging.FileHandler python.logging.FileHandler-delay
# polyglot-covers: python.logging.FileHandler-encoding-errors
# polyglot-covers: python.logging.NullHandler python.logging.NullHandler-createLock

import io
import logging


class CollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(self.format(record))


class FlushTrackingStream(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flush_count = 0

    def flush(self):
        self.flush_count += 1
        super().flush()


def test_logger_applies_handler_level_and_filter_before_emit():
    """直接调用 handler.handle 不检查 level；正常 workflow 应经 Logger.callHandlers。"""

    logger = logging.getLogger("polyglot.case188.handler-gates")
    handler = CollectingHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    handler.addFilter(lambda record: record.getMessage() != "blocked")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        logger.info("too low")
        logger.warning("blocked")
        logger.error("accepted")
        assert handler.messages == ["ERROR:accepted"]
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_stream_handler_can_switch_stream_and_customize_the_terminator():
    """setStream 先 flush 旧流并返回它；传入同一对象时不做任何事。"""

    first = FlushTrackingStream()
    second = FlushTrackingStream()
    handler = logging.StreamHandler(first)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.terminator = "|"
    first_record = logging.makeLogRecord({"msg": "first", "args": ()})
    second_record = logging.makeLogRecord({"msg": "second", "args": ()})

    handler.handle(first_record)
    flushes_after_emit = first.flush_count
    previous = handler.setStream(second)
    unchanged = handler.setStream(second)
    handler.handle(second_record)

    assert first.getvalue() == "first|"
    assert second.getvalue() == "second|"
    assert previous is first
    assert first.flush_count == flushes_after_emit + 1
    assert unchanged is None
    handler.close()


def test_delayed_file_handler_opens_on_first_emit_with_requested_encoding(tmp_path):
    """delay 避免仅构造配置就创建文件；close 后由调用方负责不再 emit。"""

    path = tmp_path / "application.log"
    handler = logging.FileHandler(
        path,
        mode="w",
        encoding="utf-8",
        delay=True,
        errors="strict",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    assert handler.stream is None
    assert path.exists() is False
    handler.handle(logging.makeLogRecord({"msg": "中文日志", "args": ()}))
    assert handler.stream is not None
    handler.close()

    assert path.read_text(encoding="utf-8") == "中文日志\n"
    assert handler.stream is None


def test_null_handler_is_a_noop_with_no_thread_lock():
    """NullHandler 明示“库不选择输出目标”，其 createLock 特意把 lock 设为 None。"""

    handler = logging.NullHandler()
    record = logging.makeLogRecord({"msg": "discarded", "args": ()})

    assert handler.lock is None
    assert handler.createLock() is None
    assert handler.handle(record) is None
    handler.close()
