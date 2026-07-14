"""189｜``logging`` 模块级配置、custom level、logger class 与 shutdown。

``basicConfig`` 默认只在 root 没有 handler 时生效，``force=True`` 才移除并关闭旧
handler。由于它和 ``shutdown`` 会改变整个进程，本文件在隔离子进程中演示这两条路径，
避免损坏 pytest 自身的捕获 handler。其他全局 hook 也都在 finally 中恢复。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.basicConfig python.logging.basicConfig-noop
# polyglot-covers: python.logging.basicConfig-force python.logging.basicConfig-stream
# polyglot-covers: python.logging.basicConfig-format python.logging.basicConfig-level
# polyglot-covers: python.logging.shutdown python.logging.Handler.close
# polyglot-covers: python.logging.addLevelName python.logging.getLevelName
# polyglot-covers: python.logging.Logger.log python.logging.custom-level
# polyglot-covers: python.logging.getLoggerClass python.logging.setLoggerClass
# polyglot-covers: python.logging.custom-Logger-class

import json
import logging
import subprocess
import sys
import textwrap


def _run_isolated(script):
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_basic_config_is_one_shot_unless_force_replaces_root_handlers():
    """第二次普通调用是 no-op；force 后的新 level/stream/format 才生效。"""

    completed = _run_isolated(
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

    completed = _run_isolated(
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
