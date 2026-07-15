"""083｜``logging`` logger 层级、有效级别与 record 传播。

logger 名称按点号形成层级；非 root logger 的 ``NOTSET`` 会继承首个祖先有效级别。
record 一旦由源 logger 接受，传播阶段会直接交给祖先的 handler，不再检查祖先 logger
自身的 level/filter；handler 的 level/filter 仍然生效。这一区别常导致误判和重复日志。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.getLogger python.logging.logger-singleton-by-name
# polyglot-covers: python.logging.logger-name-hierarchy python.logging.Logger.parent
# polyglot-covers: python.logging.Logger.setLevel python.logging.NOTSET-inheritance
# polyglot-covers: python.logging.Logger.getEffectiveLevel
# polyglot-covers: python.logging.Logger.isEnabledFor python.logging.Logger.disabled
# polyglot-covers: python.logging.Logger.propagate
# polyglot-covers: python.logging.propagation-skips-ancestor-logger-gates
# polyglot-covers: python.logging.handler-level-during-propagation
# polyglot-covers: python.logging.duplicate-handler-emission python.logging.disable



import logging
import pytest
import sys
import time
import io
import json
import subprocess
import textwrap
from contextlib import redirect_stderr
import logging.config

class HierarchyCollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class RejectEverything(logging.Filter):
    def filter(self, record):
        return False


def test_get_logger_is_identity_based_and_late_parent_creation_rewires_children():
    """先创建 child 也没关系；创建中间祖先后 Manager 会修正 parent 链。"""

    child = logging.getLogger("polyglot.case185.late.child")
    same_child = logging.getLogger("polyglot.case185.late.child")
    parent = logging.getLogger("polyglot.case185.late")

    assert child is same_child
    assert child.name == "polyglot.case185.late.child"
    assert child.parent is parent


def test_notset_delegates_to_the_first_ancestor_with_a_real_level():
    """有效级别是继承计算结果；child.level 本身仍保持 NOTSET。"""

    parent = logging.getLogger("polyglot.case185.level")
    child = logging.getLogger("polyglot.case185.level.child")
    parent.setLevel(logging.WARNING)
    child.setLevel(logging.NOTSET)
    child.disabled = False

    assert child.level == logging.NOTSET
    assert child.getEffectiveLevel() == logging.WARNING
    assert child.isEnabledFor(logging.INFO) is False
    assert child.isEnabledFor(logging.WARNING) is True

    child.disabled = True
    try:
        assert child.isEnabledFor(logging.CRITICAL) is False
    finally:
        child.disabled = False


def test_propagation_skips_ancestor_logger_gates_but_checks_handler_level():
    """祖先 logger 的 CRITICAL/filter 不挡 record；其 handler 的 level 会挡。"""

    parent = logging.getLogger("polyglot.case185.propagation")
    child = logging.getLogger("polyglot.case185.propagation.child")
    handler = HierarchyCollectingHandler()
    rejecting_filter = RejectEverything()

    parent.handlers.clear()
    child.handlers.clear()
    parent.setLevel(logging.CRITICAL)
    parent.addFilter(rejecting_filter)
    parent.propagate = False
    child.setLevel(logging.DEBUG)
    child.propagate = True
    handler.setLevel(logging.INFO)
    parent.addHandler(handler)
    try:
        child.warning("accepted by ancestor handler")
        assert [record.getMessage() for record in handler.records] == [
            "accepted by ancestor handler"
        ]

        handler.setLevel(logging.ERROR)
        child.warning("blocked by handler")
        assert len(handler.records) == 1
    finally:
        parent.removeHandler(handler)
        parent.removeFilter(rejecting_filter)
        handler.close()


def test_attaching_the_same_handler_twice_in_the_chain_duplicates_a_record():
    """传播链不对 handler 去重；通常只把 handler 挂在合适的最高祖先。"""

    parent = logging.getLogger("polyglot.case185.duplicate")
    child = logging.getLogger("polyglot.case185.duplicate.child")
    handler = HierarchyCollectingHandler()
    parent.handlers.clear()
    child.handlers.clear()
    parent.setLevel(logging.DEBUG)
    child.setLevel(logging.DEBUG)
    parent.propagate = False
    child.propagate = True
    parent.addHandler(handler)
    child.addHandler(handler)
    try:
        child.error("duplicated")
        assert len(handler.records) == 2
        assert handler.records[0] is handler.records[1]

        child.propagate = False
        child.error("local only")
        assert [record.getMessage() for record in handler.records] == [
            "duplicated",
            "duplicated",
            "local only",
        ]
    finally:
        child.removeHandler(handler)
        parent.removeHandler(handler)
        handler.close()


def test_module_disable_is_a_process_wide_gate_above_logger_levels():
    """disable(level) 屏蔽小于等于该值的事件；最后必须恢复 Manager 全局阈值。"""

    logger = logging.getLogger("polyglot.case185.global-disable")
    logger.setLevel(logging.DEBUG)
    logger.disabled = False
    previous = logging.root.manager.disable
    try:
        logging.disable(logging.ERROR)
        assert logger.isEnabledFor(logging.ERROR) is False
        assert logger.isEnabledFor(logging.CRITICAL) is True
    finally:
        logging.disable(previous)


# ``LogRecord`` 的惰性消息、caller 信息、``extra`` 与 factory hook。
#
# 日志调用把模板和参数分开保存在 record 中，直到 formatter/``getMessage`` 才执行
# ``msg % args``。低级别日志甚至不会创建 record，因此高成本值应保持惰性参数而非提前
# 拼成 f-string。``extra`` 会直接并入 record 属性，不能覆盖内建字段。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.logging.LogRecord python.logging.LogRecord.getMessage
# polyglot-covers: python.logging.lazy-percent-formatting
# polyglot-covers: python.logging.disabled-message-not-rendered
# polyglot-covers: python.logging.Logger.makeRecord python.logging.extra
# polyglot-covers: python.logging.extra-key-collision
# polyglot-covers: python.logging.stacklevel python.logging.stack_info
# polyglot-covers: python.logging.makeLogRecord
# polyglot-covers: python.logging.getLogRecordFactory python.logging.setLogRecordFactory
# polyglot-covers: python.logging.log-record-factory-chain




class RecordCollectingHandler(logging.Handler):
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
    handler = RecordCollectingHandler()
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
    handler = RecordCollectingHandler()
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
    handler = RecordCollectingHandler()
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
    handler = RecordCollectingHandler()
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


# ``LoggerAdapter``、``Filter`` 与 ``Formatter`` 的上下文处理协议。
#
# adapter 在日志调用前改写 ``msg/kwargs``，filter 在 logger 或 handler 边界决定 record
# 是否继续。Formatter 才把 record 转为文本，并支持三种模板 style。Python 3.10 的默认
# LoggerAdapter 不合并调用处 ``extra``，而是用 adapter 的字典替换它，这是常见坑。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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




class AdapterCollectingHandler(logging.Handler):
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
    handler = AdapterCollectingHandler()
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
    handler = AdapterCollectingHandler()
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


# 核心 ``Handler``、``StreamHandler``、``FileHandler`` 与 ``NullHandler``。
#
# logger 决定是否创建 record，handler 再执行自己的 level/filter、format 和 I/O。
# StreamHandler 的目标只需提供 ``write``/``flush``；FileHandler 的 ``delay=True`` 可把
# 打开文件推迟到首次 emit。库代码应安装 NullHandler，而不是擅自配置应用 root logger。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.logging.Handler python.logging.Handler.emit
# polyglot-covers: python.logging.Handler.setLevel python.logging.Handler.setFormatter
# polyglot-covers: python.logging.Handler.handle python.logging.Handler.filter
# polyglot-covers: python.logging.StreamHandler python.logging.StreamHandler.terminator
# polyglot-covers: python.logging.StreamHandler.setStream
# polyglot-covers: python.logging.StreamHandler.flush
# polyglot-covers: python.logging.FileHandler python.logging.FileHandler-delay
# polyglot-covers: python.logging.FileHandler-encoding-errors
# polyglot-covers: python.logging.NullHandler python.logging.NullHandler-createLock



class StreamCollectingHandler(logging.Handler):
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
    handler = StreamCollectingHandler()
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


# ``logging`` 模块级配置、custom level、logger class 与 shutdown。
#
# ``basicConfig`` 默认只在 root 没有 handler 时生效，``force=True`` 才移除并关闭旧
# handler。由于它和 ``shutdown`` 会改变整个进程，本文件在隔离子进程中演示这两条路径，
# 避免损坏 pytest 自身的捕获 handler。其他全局 hook 也都在 finally 中恢复。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.logging.basicConfig python.logging.basicConfig-noop
# polyglot-covers: python.logging.basicConfig-force python.logging.basicConfig-stream
# polyglot-covers: python.logging.basicConfig-format python.logging.basicConfig-level
# polyglot-covers: python.logging.shutdown python.logging.Handler.close
# polyglot-covers: python.logging.addLevelName python.logging.getLevelName
# polyglot-covers: python.logging.Logger.log python.logging.custom-level
# polyglot-covers: python.logging.getLoggerClass python.logging.setLoggerClass
# polyglot-covers: python.logging.custom-Logger-class



def _run_module_config_isolated(script):
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_basic_config_is_one_shot_unless_force_replaces_root_handlers():
    """第二次普通调用是 no-op；force 后的新 level/stream/format 才生效。"""

    completed = _run_module_config_isolated(
        """
        import io
        import json
        import logging

        first = io.StringIO()
        second = io.StringIO()
        logging.basicConfig(
            level=logging.INFO,
            stream=first,
            format="first:%(message)s",
        )
        logging.basicConfig(
            level=logging.DEBUG,
            stream=second,
            format="ignored:%(message)s",
        )
        logging.debug("still filtered")
        logging.info("before")
        logging.basicConfig(
            level=logging.DEBUG,
            stream=second,
            format="second:%(message)s",
            force=True,
        )
        logging.debug("after")
        print(json.dumps([first.getvalue(), second.getvalue()]))
        """
    )

    assert json.loads(completed.stdout) == ["first:before\n", "second:after\n"]
    assert completed.stderr == ""


def test_shutdown_flushes_and_closes_registered_handlers():
    """logging 已用 atexit 自动调用 shutdown；手工调用主要用于需明确收尾的宿主。"""

    completed = _run_module_config_isolated(
        """
        import json
        import logging

        events = []

        class TrackingHandler(logging.Handler):
            def emit(self, record):
                events.append(("emit", record.getMessage()))

            def flush(self):
                events.append(("flush", None))

            def close(self):
                events.append(("close", None))
                super().close()

        logger = logging.getLogger("isolated")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(TrackingHandler())
        logger.info("payload")
        logging.shutdown()
        print(json.dumps(events))
        """
    )

    events = json.loads(completed.stdout)
    assert events[0] == ["emit", "payload"]
    assert [event[0] for event in events[1:]] == ["flush", "close"]


def test_custom_level_name_is_bidirectional_and_logger_log_accepts_its_number():
    """level number 才参与比较；名称只用于配置和展示，冲突会覆盖映射。"""

    old_level_names = logging._levelToName.copy()
    old_name_levels = logging._nameToLevel.copy()
    logger = logging.getLogger("polyglot.case189.custom-level")
    records = []

    class Collector(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = Collector()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(25)
    logger.propagate = False
    try:
        logging.addLevelName(25, "NOTICE")
        assert logging.getLevelName(25) == "NOTICE"
        assert logging.getLevelName("NOTICE") == 25

        logger.log(25, "custom event")
        assert records[0].levelno == 25
        assert records[0].levelname == "NOTICE"
    finally:
        logger.removeHandler(handler)
        handler.close()
        # 公共 API 没有删除 custom level；仅测试清理阶段恢复内部 registry 快照。
        logging._levelToName.clear()
        logging._levelToName.update(old_level_names)
        logging._nameToLevel.clear()
        logging._nameToLevel.update(old_name_levels)


def test_set_logger_class_affects_future_get_logger_instances_only():
    """自定义类构造器只接收 name，并必须委托 Logger.__init__。"""

    previous_class = logging.getLoggerClass()

    class ContextLogger(logging.Logger):
        def __init__(self, name):
            super().__init__(name)
            self.component = "polyglot"

    existing = logging.getLogger("polyglot.case189.existing")
    try:
        logging.setLoggerClass(ContextLogger)
        created = logging.getLogger("polyglot.case189.created-after-hook")

        assert isinstance(created, ContextLogger)
        assert created.component == "polyglot"
        assert isinstance(existing, ContextLogger) is False
    finally:
        logging.setLoggerClass(previous_class)


# ``logging`` 与 warnings、last-resort 输出及 handler 内部错误。
#
# ``captureWarnings`` 把 warning 格式化后发往 ``py.warnings`` logger。没有任何 handler
# 可处理 record 时，``lastResort`` 只兜底 WARNING 以上事件。handler I/O 失败通常不会
# 回抛给业务调用方；开发期的 ``raiseExceptions`` 只控制是否把诊断打印到 stderr。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.logging.captureWarnings python.logging.py-warnings-logger
# polyglot-covers: python.logging.lastResort python.logging.no-handler-fallback
# polyglot-covers: python.logging.raiseExceptions python.logging.Handler.handleError
# polyglot-covers: python.logging.Logger.exception python.logging.exc_info
# polyglot-covers: python.logging.Logger.getChild python.logging.Logger.hasHandlers



class ErrorCollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class BrokenStream:
    def write(self, text):
        raise OSError("sink unavailable")

    def flush(self):
        pass


def test_capture_warnings_redirects_formatted_warning_to_named_logger():
    """用子进程隔离 warnings.showwarning 和 logging 的 process-global hook。"""

    script = textwrap.dedent(
        """
        import json
        import logging
        import warnings

        records = []

        class Collector(logging.Handler):
            def emit(self, record):
                records.append({
                    "name": record.name,
                    "level": record.levelno,
                    "message": record.getMessage(),
                })

        logger = logging.getLogger("py.warnings")
        logger.handlers[:] = [Collector()]
        logger.propagate = False
        logger.setLevel(logging.WARNING)
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            logging.captureWarnings(True)
            try:
                warnings.warn("legacy option", DeprecationWarning)
            finally:
                logging.captureWarnings(False)
        print(json.dumps(records))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    records = json.loads(completed.stdout)

    assert records[0]["name"] == "py.warnings"
    assert records[0]["level"] == logging.WARNING
    assert "DeprecationWarning: legacy option" in records[0]["message"]
    assert completed.stderr == ""


def test_last_resort_only_handles_warning_or_higher_when_no_handler_exists():
    """lastResort 的默认格式仅输出 message，不带 root 风格的 level/name 前缀。"""

    logger = logging.getLogger("polyglot.case190.last-resort")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    output = io.StringIO()

    with redirect_stderr(output):
        logger.info("not emitted")
        logger.warning("emergency")

    assert output.getvalue() == "emergency\n"


def test_raise_exceptions_controls_diagnostics_not_business_propagation():
    """StreamHandler 捕获 emit I/O 错误；开关只决定 handleError 是否打印诊断。"""

    handler = logging.StreamHandler(BrokenStream())
    record = logging.makeLogRecord({"msg": "payload", "args": ()})
    previous = logging.raiseExceptions
    verbose_output = io.StringIO()
    quiet_output = io.StringIO()
    try:
        logging.raiseExceptions = True
        with redirect_stderr(verbose_output):
            assert handler.handle(record) is True

        logging.raiseExceptions = False
        with redirect_stderr(quiet_output):
            assert handler.handle(record) is True
    finally:
        logging.raiseExceptions = previous
        handler.close()

    assert "--- Logging error ---" in verbose_output.getvalue()
    assert "sink unavailable" in verbose_output.getvalue()
    assert quiet_output.getvalue() == ""


def test_logger_exception_attaches_current_exception_tuple():
    """exception 等价于 error(..., exc_info=True)，必须在异常处理上下文中调用。"""

    logger = logging.getLogger("polyglot.case190.exception")
    handler = ErrorCollectingHandler()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    try:
        try:
            raise LookupError("missing")
        except LookupError:
            logger.exception("lookup failed")

        record = handler.records[0]
        assert record.getMessage() == "lookup failed"
        assert record.exc_info[0] is LookupError
        assert isinstance(record.exc_info[1], LookupError)
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_get_child_builds_hierarchical_name_and_has_handlers_walks_ancestors():
    """hasHandlers 沿 parent 查找，遇到 propagate=False 就停止。"""

    parent = logging.getLogger("polyglot.case190.parent")
    child = parent.getChild("service.worker")
    handler = logging.NullHandler()
    parent.handlers.clear()
    child.handlers.clear()
    parent.addHandler(handler)
    parent.propagate = False
    child.propagate = True
    try:
        assert child is logging.getLogger("polyglot.case190.parent.service.worker")
        assert child.hasHandlers() is True

        child.propagate = False
        assert child.hasHandlers() is False
    finally:
        parent.removeHandler(handler)
        handler.close()


# ``logging.config.dictConfig`` schema、对象连接与增量更新。
#
# 完整 dictConfig 会重建全局 handler registry，因此主 workflow 在隔离子进程运行。
# ``ext://`` 解析外部对象，``cfg://`` 引用当前配置内部值，``'()'`` 调用用户 factory。
# 这些动态解析能力很灵活，也意味着配置必须来自受信任来源。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.logging.config.dictConfig
# polyglot-covers: python.logging.config.dictionary-schema-version
# polyglot-covers: python.logging.config.formatters python.logging.config.filters
# polyglot-covers: python.logging.config.handlers python.logging.config.loggers
# polyglot-covers: python.logging.config.disable_existing_loggers
# polyglot-covers: python.logging.config.user-defined-object-factory
# polyglot-covers: python.logging.config.ext-object-reference
# polyglot-covers: python.logging.config.cfg-object-reference
# polyglot-covers: python.logging.config.incremental-configuration
# polyglot-covers: python.logging.config.incremental-levels-only
# polyglot-covers: python.logging.config.dictConfigClass




def _run_dict_config_isolated(script):
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_full_dict_config_wires_factories_filters_formatters_and_references():
    """cfg 值传给 factory，ext stream 解析为 stderr；两者都在配置阶段解析。"""

    completed = _run_dict_config_isolated(
        """
        import json
        import logging
        import logging.config

        class TenantFilter(logging.Filter):
            def __init__(self, tenant):
                super().__init__()
                self.tenant = tenant

            def filter(self, record):
                return getattr(record, "tenant", None) == self.tenant

        class ListHandler(logging.Handler):
            def __init__(self, prefix):
                super().__init__()
                self.prefix = prefix
                self.messages = []

            def emit(self, record):
                self.messages.append(self.prefix + ":" + self.format(record))

        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "shared": {"prefix": "CFG"},
            "formatters": {
                "compact": {"format": "%(levelname)s|%(tenant)s|%(message)s"}
            },
            "filters": {
                "blue": {"()": TenantFilter, "tenant": "blue"}
            },
            "handlers": {
                "memory": {
                    "()": ListHandler,
                    "prefix": "cfg://shared.prefix",
                    "level": "INFO",
                    "formatter": "compact",
                    "filters": ["blue"],
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "level": "ERROR",
                    "formatter": "compact",
                    "filters": ["blue"],
                },
            },
            "loggers": {
                "polyglot.configured": {
                    "level": "DEBUG",
                    "handlers": ["memory", "console"],
                    "propagate": False,
                }
            },
        }
        logging.config.dictConfig(config)
        logger = logging.getLogger("polyglot.configured")
        logger.info("accepted", extra={"tenant": "blue"})
        logger.error("rejected", extra={"tenant": "red"})
        logger.error("failure", extra={"tenant": "blue"})
        memory = next(
            handler for handler in logger.handlers
            if isinstance(handler, ListHandler)
        )
        print(json.dumps(memory.messages))
        """
    )

    assert json.loads(completed.stdout) == [
        "CFG:INFO|blue|accepted",
        "CFG:ERROR|blue|failure",
    ]
    assert completed.stderr == "ERROR|blue|failure\n"


def test_omitting_disable_existing_loggers_disables_unmentioned_loggers():
    """默认值是 True；应用增量迁移配置时这是最常见的静默丢日志原因之一。"""

    completed = _run_dict_config_isolated(
        """
        import json
        import logging
        import logging.config

        stale = logging.getLogger("polyglot.stale")
        stale.disabled = False
        logging.config.dictConfig({
            "version": 1,
            "handlers": {},
            "loggers": {
                "polyglot.kept": {
                    "level": "INFO",
                    "handlers": [],
                    "propagate": False,
                }
            },
        })
        print(json.dumps({
            "stale_disabled": stale.disabled,
            "kept_disabled": logging.getLogger("polyglot.kept").disabled,
        }))
        """
    )

    assert json.loads(completed.stdout) == {
        "stale_disabled": True,
        "kept_disabled": False,
    }


def test_incremental_config_only_changes_existing_handler_and_logger_levels():
    """incremental=True 忽略 formatter/filter sections，不创建新的 object graph。"""

    handler = logging.NullHandler()
    handler.name = "polyglot-case191-handler"
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("polyglot.case191.incremental")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        logging.config.dictConfig(
            {
                "version": 1,
                "incremental": True,
                "formatters": {"ignored": {"format": "%(message)s"}},
                "handlers": {"polyglot-case191-handler": {"level": "ERROR"}},
                "loggers": {
                    "polyglot.case191.incremental": {
                        "level": "WARNING",
                        "propagate": True,
                    }
                },
            }
        )

        assert handler.level == logging.ERROR
        assert logger.level == logging.WARNING
        assert logger.propagate is True
        assert handler.formatter is None
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_dict_config_delegates_to_replaceable_configurator_class(monkeypatch):
    """dictConfigClass 是 package-wide extension point，替代类接收原配置对象。"""

    calls = []

    class RecordingConfigurator:
        def __init__(self, config):
            calls.append(("init", config))

        def configure(self):
            calls.append(("configure", None))

    config = {"version": 1}
    monkeypatch.setattr(logging.config, "dictConfigClass", RecordingConfigurator)
    logging.config.dictConfig(config)

    assert calls == [("init", config), ("configure", None)]


def test_dict_config_rejects_unknown_schema_version_before_reconfiguration():
    """version 是必填 schema discriminator；Python 3.10 只接受整数 1。"""

    with pytest.raises(ValueError, match="Unsupported version"):
        logging.config.dictConfig({"version": 2})


# ``logging.config.fileConfig``、INI 插值与配置 listener 的安全边界。
#
# fileConfig 使用 configparser 格式，并会重建全局 handler，因此实际加载放在隔离子进程。
# ``listen`` 可创建接收线程，但启动后会使用 socket 且配置内容可能导入/执行对象；仓库禁止
# 网络，所以这里只验证未启动的构造协议和 verify hook，不打开端口。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.logging.config.fileConfig
# polyglot-covers: python.logging.config.fileConfig-file-like
# polyglot-covers: python.logging.config.fileConfig-defaults
# polyglot-covers: python.logging.config.fileConfig-disable-existing-loggers
# polyglot-covers: python.logging.config.ini-loggers
# polyglot-covers: python.logging.config.ini-handlers
# polyglot-covers: python.logging.config.ini-formatters
# polyglot-covers: python.logging.config.listen python.logging.config.listen-verify
# polyglot-covers: python.logging.config.stopListening
# polyglot-covers: python.logging.config.untrusted-configuration-risk



def test_file_config_accepts_text_stream_and_configparser_defaults():
    """handler args 会在 logging namespace 中 eval；这里只加载仓库内固定配置。"""

    script = textwrap.dedent(
        """
        import io
        import json
        import logging
        import logging.config

        existing = logging.getLogger("polyglot.preexisting")
        existing.disabled = False
        ini = io.StringIO('''
        [loggers]
        keys=root,service

        [handlers]
        keys=console

        [formatters]
        keys=compact

        [logger_root]
        level=WARNING
        handlers=

        [logger_service]
        level=DEBUG
        handlers=console
        qualname=polyglot.file-config
        propagate=0

        [handler_console]
        class=StreamHandler
        level=INFO
        formatter=compact
        args=(%(stream)s,)

        [formatter_compact]
        format=%(levelname)s|%(message)s
        ''')
        logging.config.fileConfig(
            ini,
            defaults={"stream": "sys.stderr"},
            disable_existing_loggers=False,
        )
        logger = logging.getLogger("polyglot.file-config")
        logger.debug("filtered by handler")
        logger.info("configured")
        print(json.dumps({
            "logger_level": logger.level,
            "handler_level": logger.handlers[0].level,
            "propagate": logger.propagate,
            "existing_disabled": existing.disabled,
        }))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stderr == "INFO|configured\n"
    assert json.loads(completed.stdout) == {
        "logger_level": logging.DEBUG,
        "handler_level": logging.INFO,
        "propagate": 0,
        "existing_disabled": False,
    }


def test_listen_returns_an_unstarted_thread_carrying_port_and_verify_hook():
    """构造本身不绑定 socket；调用 start 才进入接收循环，本案例刻意不启动。"""

    def verify(payload):
        return payload if payload.startswith(b"trusted:") else None

    server = logging.config.listen(port=0, verify=verify)

    assert server.port == 0
    assert server.verify is verify
    assert server.is_alive() is False
    logging.config.stopListening()
