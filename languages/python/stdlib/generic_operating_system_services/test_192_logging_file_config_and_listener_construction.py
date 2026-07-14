"""192｜``logging.config.fileConfig``、INI 插值与配置 listener 的安全边界。

fileConfig 使用 configparser 格式，并会重建全局 handler，因此实际加载放在隔离子进程。
``listen`` 可创建接收线程，但启动后会使用 socket 且配置内容可能导入/执行对象；仓库禁止
网络，所以这里只验证未启动的构造协议和 verify hook，不打开端口。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import json
import logging.config
import subprocess
import sys
import textwrap


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
