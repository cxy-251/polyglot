"""195｜``QueueHandler``/``QueueListener`` 的 record preparation 与线程管线。

QueueHandler 在生产线程中先 format，再复制 record 并清除难以 pickle 的字段；原 record
不会被污染。QueueListener 在后台线程依次派发，``stop`` 写 sentinel 并 join，所以无需
sleep 也能确定此前的 FIFO record 已处理。是否检查目标 handler.level 由参数显式控制。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import logging
from logging.handlers import QueueHandler
from logging.handlers import QueueListener
import queue


class CollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class DisplayValue:
    def __str__(self):
        return "VALUE"


def _record(level, message, args=()):
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
    original = _record(logging.INFO, "value=%s", (DisplayValue(),))

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
    record = _record(logging.INFO, "direct")

    handler.enqueue(record)

    assert event_queue.get_nowait() is record
    handler.close()


def test_listener_stop_waits_for_fifo_records_and_respects_handler_levels():
    """stop 的 sentinel 排在既有事件后，join 返回时这些事件已完成派发。"""

    event_queue = queue.Queue()
    producer = QueueHandler(event_queue)
    warning_target = CollectingHandler()
    error_target = CollectingHandler()
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

    target = CollectingHandler()
    target.setLevel(logging.CRITICAL)
    listener = QueueListener(queue.Queue(), target, respect_handler_level=False)
    record = _record(logging.INFO, "offered")

    assert listener.prepare(record) is record
    listener.handle(record)
    assert target.records == [record]
    target.close()
