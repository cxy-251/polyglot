"""190｜``logging`` 与 warnings、last-resort 输出及 handler 内部错误。

``captureWarnings`` 把 warning 格式化后发往 ``py.warnings`` logger。没有任何 handler
可处理 record 时，``lastResort`` 只兜底 WARNING 以上事件。handler I/O 失败通常不会
回抛给业务调用方；开发期的 ``raiseExceptions`` 只控制是否把诊断打印到 stderr。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.captureWarnings python.logging.py-warnings-logger
# polyglot-covers: python.logging.lastResort python.logging.no-handler-fallback
# polyglot-covers: python.logging.raiseExceptions python.logging.Handler.handleError
# polyglot-covers: python.logging.Logger.exception python.logging.exc_info
# polyglot-covers: python.logging.Logger.getChild python.logging.Logger.hasHandlers

from contextlib import redirect_stderr
import io
import json
import logging
import subprocess
import sys
import textwrap


class CollectingHandler(logging.Handler):
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
    handler = CollectingHandler()
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
