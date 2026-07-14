"""194｜``BufferingHandler`` 与 ``MemoryHandler`` 的 flush 契约。

BufferingHandler 到达 capacity 时调用可覆盖的 ``flush``；基类实现仅清空 buffer。
MemoryHandler 则把已缓存 record 依次交给 target，可由容量或 ``flushLevel`` 触发。
它直接调用 target.handle，因此 target.level 不会像 Logger.callHandlers 中那样自动检查。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import logging
from logging.handlers import BufferingHandler
from logging.handlers import MemoryHandler


class CollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def _record(level, message):
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
    first = _record(logging.INFO, "first")
    second = _record(logging.INFO, "second")

    assert handler.shouldFlush(first) is False
    handler.handle(first)
    assert handler.buffer == [first]
    handler.handle(second)
    assert handler.buffer == []
    handler.close()


def test_memory_handler_flush_level_forwards_the_whole_buffer_in_order():
    """ERROR 不只发送自己；它会把此前 INFO/WARNING 一起按原顺序交给 target。"""

    target = CollectingHandler()
    memory = MemoryHandler(
        capacity=10,
        flushLevel=logging.ERROR,
        target=target,
        flushOnClose=False,
    )
    try:
        memory.handle(_record(logging.INFO, "info"))
        memory.handle(_record(logging.WARNING, "warning"))
        assert [record.getMessage() for record in memory.buffer] == ["info", "warning"]

        memory.handle(_record(logging.ERROR, "error"))
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

    target = CollectingHandler()
    target.setLevel(logging.CRITICAL)
    memory = MemoryHandler(
        capacity=1,
        target=target,
        flushOnClose=False,
    )
    try:
        memory.handle(_record(logging.INFO, "still forwarded"))
        assert [record.getMessage() for record in target.records] == ["still forwarded"]
    finally:
        memory.close()
        target.close()


def test_set_target_and_flush_on_close_control_final_delivery():
    """flushOnClose=False 可在异常收尾时丢弃尾部 buffer；True 保持兼容的发送行为。"""

    delivered = CollectingHandler()
    discarded = CollectingHandler()
    flushing = MemoryHandler(capacity=10, target=None, flushOnClose=True)
    non_flushing = MemoryHandler(
        capacity=10,
        target=discarded,
        flushOnClose=False,
    )

    flushing.setTarget(delivered)
    flushing.handle(_record(logging.INFO, "deliver on close"))
    non_flushing.handle(_record(logging.INFO, "discard on close"))
    flushing.close()
    non_flushing.close()

    assert [record.getMessage() for record in delivered.records] == [
        "deliver on close"
    ]
    assert discarded.records == []
    delivered.close()
    discarded.close()
