"""191｜``logging.config.dictConfig`` schema、对象连接与增量更新。

完整 dictConfig 会重建全局 handler registry，因此主 workflow 在隔离子进程运行。
``ext://`` 解析外部对象，``cfg://`` 引用当前配置内部值，``'()'`` 调用用户 factory。
这些动态解析能力很灵活，也意味着配置必须来自受信任来源。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import json
import logging
import logging.config
import subprocess
import sys
import textwrap

import pytest


def _run_isolated(script):
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_full_dict_config_wires_factories_filters_formatters_and_references():
    """cfg 值传给 factory，ext stream 解析为 stderr；两者都在配置阶段解析。"""

    completed = _run_isolated(
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

    completed = _run_isolated(
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
