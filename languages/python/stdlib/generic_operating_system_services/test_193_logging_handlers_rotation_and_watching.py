"""193｜``logging.handlers`` 文件监视、尺寸轮转与时间轮转。

WatchedFileHandler 通过 device/inode 发现外部轮转，适合 Unix 上由 logrotate 管理的文件。
RotatingFileHandler 在写入前按预计尺寸轮转；TimedRotatingFileHandler 的旧文件清理依赖
可排序 suffix。``namer``/``rotator`` 可定制名字和搬运方式，但必须保持快速、确定。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.handlers.WatchedFileHandler
# polyglot-covers: python.logging.handlers.WatchedFileHandler.reopenIfNeeded
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.namer
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.rotator
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.rotation_filename
# polyglot-covers: python.logging.handlers.BaseRotatingHandler.rotate
# polyglot-covers: python.logging.handlers.RotatingFileHandler
# polyglot-covers: python.logging.handlers.RotatingFileHandler-size-rollover
# polyglot-covers: python.logging.handlers.RotatingFileHandler-backupCount
# polyglot-covers: python.logging.handlers.TimedRotatingFileHandler
# polyglot-covers: python.logging.handlers.TimedRotatingFileHandler.computeRollover
# polyglot-covers: python.logging.handlers.TimedRotatingFileHandler.getFilesToDelete

import logging
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler
from logging.handlers import WatchedFileHandler
import os

import pytest


@pytest.mark.skipif(os.name != "posix", reason="inode-based external rotation is Unix-specific")
def test_watched_file_handler_reopens_after_external_rename(tmp_path):
    """外部工具 move 原文件并创建同名新文件后，下一次 emit 自动切换 inode。"""

    active = tmp_path / "application.log"
    rotated = tmp_path / "application.log.old"
    handler = WatchedFileHandler(active, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("polyglot.case193.watched")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("before rotation")
        os.rename(active, rotated)
        active.write_text("", encoding="utf-8")
        logger.info("after rotation")
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert rotated.read_text(encoding="utf-8") == "before rotation\n"
    assert active.read_text(encoding="utf-8") == "after rotation\n"


def test_rotating_base_callbacks_customize_destination_and_file_move(tmp_path):
    """rotation_filename 调 namer，rotate 调 rotator；callback 自己负责实际搬运。"""

    log_path = tmp_path / "callback.log"
    source = tmp_path / "source.log"
    destination = tmp_path / "destination.log.gz"
    source.write_text("payload", encoding="utf-8")
    moved = []
    handler = RotatingFileHandler(log_path, delay=True)
    handler.namer = lambda default_name: default_name + ".gz"

    def rotator(source_name, destination_name):
        moved.append((source_name, destination_name))
        os.replace(source_name, destination_name)

    handler.rotator = rotator
    try:
        assert handler.rotation_filename("archive.log.1") == "archive.log.1.gz"
        handler.rotate(str(source), str(destination))
    finally:
        handler.close()

    assert moved == [(str(source), str(destination))]
    assert destination.read_text(encoding="utf-8") == "payload"
    assert source.exists() is False


def test_size_rotation_keeps_numbered_backups_newest_first(tmp_path):
    """达到阈值的那条记录写入新文件；``.1`` 始终是最近一次旧 active 文件。"""

    path = tmp_path / "sized.log"
    handler = RotatingFileHandler(
        path,
        mode="a",
        maxBytes=12,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("polyglot.case193.size")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("first")
        logger.info("second")
        logger.info("third")
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert path.read_text(encoding="utf-8") == "third\n"
    assert (tmp_path / "sized.log.1").read_text(encoding="utf-8") == "second\n"
    assert (tmp_path / "sized.log.2").read_text(encoding="utf-8") == "first\n"


def test_timed_rotation_computes_interval_and_deletes_oldest_matching_suffix(tmp_path):
    """清理只识别 handler suffix regex；无关文件不会误删。"""

    path = tmp_path / "timed.log"
    handler = TimedRotatingFileHandler(
        path,
        when="S",
        interval=5,
        backupCount=2,
        utc=True,
        delay=True,
    )
    names = [
        "timed.log.2024-01-01_00-00-00",
        "timed.log.2024-01-01_00-00-05",
        "timed.log.2024-01-01_00-00-10",
    ]
    for name in names:
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "timed.log.notes").write_text("keep", encoding="utf-8")
    try:
        assert handler.computeRollover(100) == 105
        assert handler.getFilesToDelete() == [str(tmp_path / names[0])]
    finally:
        handler.close()
