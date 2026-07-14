"""186｜``LogRecord`` 的惰性消息、caller 信息、``extra`` 与 factory hook。

日志调用把模板和参数分开保存在 record 中，直到 formatter/``getMessage`` 才执行
``msg % args``。低级别日志甚至不会创建 record，因此高成本值应保持惰性参数而非提前
拼成 f-string。``extra`` 会直接并入 record 属性，不能覆盖内建字段。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.LogRecord python.logging.LogRecord.getMessage
# polyglot-covers: python.logging.lazy-percent-formatting
# polyglot-covers: python.logging.disabled-message-not-rendered
# polyglot-covers: python.logging.Logger.makeRecord python.logging.extra
# polyglot-covers: python.logging.extra-key-collision
# polyglot-covers: python.logging.stacklevel python.logging.stack_info
# polyglot-covers: python.logging.makeLogRecord
# polyglot-covers: python.logging.getLogRecordFactory python.logging.setLogRecordFactory
# polyglot-covers: python.logging.log-record-factory-chain

import logging

import pytest


class CollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LazyValue:
    def __init__(self):
        self.render_count = 0

    def __str__(self):
        self.render_count += 1
        return "EXPENSIVE"


def test_message_template_and_args_remain_lazy_until_get_message():
    """传 ``logger.info('x=%s', value)`` 才能利用级别短路和延迟格式化。"""

    logger = logging.getLogger("polyglot.case186.lazy")
    handler = CollectingHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    value = LazyValue()
    try:
        logger.debug("value=%s", value)
        assert value.render_count == 0
        assert handler.records == []

        logger.warning("value=%s", value)
        record = handler.records[0]
        assert record.msg == "value=%s"
        assert record.args == (value,)
        assert value.render_count == 0
        assert record.getMessage() == "value=EXPENSIVE"
        assert value.render_count == 1
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_extra_adds_domain_fields_but_cannot_replace_reserved_record_fields():
    """extra key 与 levelname/message 等内建字段冲突时立即抛 KeyError。"""

    logger = logging.getLogger("polyglot.case186.extra")
    handler = CollectingHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("accepted", extra={"request_id": "req-7"})
        assert handler.records[0].request_id == "req-7"

        with pytest.raises(KeyError, match="levelname"):
            logger.info("invalid", extra={"levelname": "FAKE"})
    finally:
        logger.removeHandler(handler)
        handler.close()


def _logging_wrapper(logger):
    logger.warning("from wrapper", stacklevel=2, stack_info=True)


def test_stacklevel_reports_the_wrapper_caller_and_stack_info_is_separate():
    """stacklevel 修正 pathname/funcName；stack_info 是调用栈，不是异常 traceback。"""

    logger = logging.getLogger("polyglot.case186.caller")
    handler = CollectingHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    try:
        _logging_wrapper(logger)
        record = handler.records[0]
        assert record.funcName == (
            "test_stacklevel_reports_the_wrapper_caller_and_stack_info_is_separate"
        )
        assert record.stack_info.startswith("Stack (most recent call last):")
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_make_log_record_reconstructs_a_record_from_attribute_mapping():
    """网络/队列接收端可从字典重建 record；自定义字段也会保留。"""

    record = logging.makeLogRecord(
        {
            "name": "polyglot.remote",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "item=%s",
            "args": (3,),
            "request_id": "remote-1",
        }
    )

    assert record.getMessage() == "item=3"
    assert record.request_id == "remote-1"
    assert record.levelno == logging.INFO


def test_record_factory_can_chain_and_add_cross_cutting_context():
    """自定义 factory 应调用旧 factory，再增添不与其他库冲突的属性。"""

    previous_factory = logging.getLogRecordFactory()

    def contextual_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        record.deployment = "test"
        return record

    logger = logging.getLogger("polyglot.case186.factory")
    handler = CollectingHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logging.setLogRecordFactory(contextual_factory)
        logger.info("created by custom factory")
        assert handler.records[0].deployment == "test"
    finally:
        logging.setLogRecordFactory(previous_factory)
        logger.removeHandler(handler)
        handler.close()
