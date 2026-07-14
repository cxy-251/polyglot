"""187｜``LoggerAdapter``、``Filter`` 与 ``Formatter`` 的上下文处理协议。

adapter 在日志调用前改写 ``msg/kwargs``，filter 在 logger 或 handler 边界决定 record
是否继续。Formatter 才把 record 转为文本，并支持三种模板 style。Python 3.10 的默认
LoggerAdapter 不合并调用处 ``extra``，而是用 adapter 的字典替换它，这是常见坑。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.LoggerAdapter python.logging.LoggerAdapter.process
# polyglot-covers: python.logging.LoggerAdapter-extra-replacement
# polyglot-covers: python.logging.custom-LoggerAdapter-extra-merge
# polyglot-covers: python.logging.Filter python.logging.Filter-name-prefix
# polyglot-covers: python.logging.callable-filter python.logging.Handler.addFilter
# polyglot-covers: python.logging.Formatter python.logging.Formatter-style-percent
# polyglot-covers: python.logging.Formatter-style-brace python.logging.Formatter-style-dollar
# polyglot-covers: python.logging.Formatter-defaults python.logging.Formatter-validate
# polyglot-covers: python.logging.Formatter.converter python.logging.Formatter.formatTime
# polyglot-covers: python.logging.Formatter.formatException

import logging
import sys
import time

import pytest


class CollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class MergingAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        merged = dict(self.extra)
        merged.update(kwargs.get("extra", {}))
        kwargs["extra"] = merged
        return msg, kwargs


def test_default_adapter_replaces_call_extra_while_custom_adapter_can_merge_it():
    """3.10 默认 adapter 丢弃调用处 extra；需要覆盖 process 才能定义合并优先级。"""

    logger = logging.getLogger("polyglot.case187.adapter")
    handler = CollectingHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        adapter = logging.LoggerAdapter(logger, {"tenant": "base"})
        adapter.info("default", extra={"tenant": "call", "request_id": "lost"})

        merging = MergingAdapter(logger, {"tenant": "base", "region": "east"})
        merging.info("merged", extra={"tenant": "call", "request_id": "kept"})

        default_record, merged_record = handler.records
        assert default_record.tenant == "base"
        assert not hasattr(default_record, "request_id")
        assert merged_record.tenant == "call"
        assert merged_record.region == "east"
        assert merged_record.request_id == "kept"
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_named_filter_matches_exact_logger_or_dot_delimited_descendants():
    """字符串前缀还要求点号边界，所以 app.api2 不是 app.api 的 descendant。"""

    name_filter = logging.Filter("app.api")

    assert name_filter.filter(logging.makeLogRecord({"name": "app.api"})) is True
    assert name_filter.filter(logging.makeLogRecord({"name": "app.api.client"})) is True
    assert name_filter.filter(logging.makeLogRecord({"name": "app.api2"})) is False
    assert logging.Filter().filter(logging.makeLogRecord({"name": "anything"})) is True


def test_handler_accepts_any_callable_filter_and_applies_all_filters():
    """filter 不必继承 Filter；返回 false 的任意 callable 都会短路 emit。"""

    logger = logging.getLogger("polyglot.case187.callable-filter")
    handler = CollectingHandler()
    handler.addFilter(lambda record: getattr(record, "tenant", None) == "allowed")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("blocked", extra={"tenant": "other"})
        logger.info("accepted", extra={"tenant": "allowed"})
        assert [record.getMessage() for record in handler.records] == ["accepted"]
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_formatter_styles_render_the_same_record_with_different_syntaxes():
    """style 只决定格式模板语法；日志 message 仍始终使用 ``msg % args``。"""

    record = logging.makeLogRecord(
        {
            "name": "polyglot",
            "levelname": "INFO",
            "levelno": logging.INFO,
            "msg": "item=%s",
            "args": (7,),
        }
    )

    percent = logging.Formatter("%(levelname)s:%(message)s")
    brace = logging.Formatter("{levelname}:{message}", style="{")
    dollar = logging.Formatter("$levelname:$message", style="$")

    assert percent.format(record) == "INFO:item=7"
    assert brace.format(record) == "INFO:item=7"
    assert dollar.format(record) == "INFO:item=7"


def test_formatter_defaults_are_fallbacks_and_validation_catches_style_mismatch():
    """defaults 填补缺失字段；record/extra 中的同名值优先于 fallback。"""

    formatter = logging.Formatter(
        "%(client_ip)s %(message)s",
        defaults={"client_ip": "-"},
    )
    missing = logging.makeLogRecord({"msg": "anonymous", "args": ()})
    present = logging.makeLogRecord(
        {"msg": "identified", "args": (), "client_ip": "127.0.0.1"}
    )

    assert formatter.format(missing) == "- anonymous"
    assert formatter.format(present) == "127.0.0.1 identified"
    with pytest.raises(ValueError):
        logging.Formatter("{message}", style="%", validate=True)


def test_formatter_can_use_utc_and_formats_exception_information():
    """converter 是时间 hook；exc_info 则在正文后追加已格式化 traceback。"""

    record = logging.makeLogRecord(
        {"msg": "failed", "args": (), "created": 0.0, "msecs": 0.0}
    )
    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d")
    formatter.converter = time.gmtime
    assert formatter.format(record) == "1970-01-01 failed"

    try:
        1 / 0
    except ZeroDivisionError:
        failure = logging.makeLogRecord(
            {"msg": "division", "args": (), "exc_info": sys.exc_info()}
        )

    rendered = logging.Formatter("%(message)s").format(failure)
    assert rendered.startswith("division\nTraceback (most recent call last):")
    assert "ZeroDivisionError" in rendered
    assert failure.exc_text is not None
