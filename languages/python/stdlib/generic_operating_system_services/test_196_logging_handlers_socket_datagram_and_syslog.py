"""196｜Socket/Datagram handler 的 wire record 与 SysLog priority 映射。

SocketHandler 发送的是四字节大端长度加 pickle record 字典，而不是文本 formatter 输出；
接收端应校验来源，因为 pickle 不能用于不可信数据。这里仅调用离线 ``makePickle``，
不创建连接。SysLog 的 facility/priority 组合也可在不打开 socket 时验证。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.handlers.SocketHandler
# polyglot-covers: python.logging.handlers.SocketHandler.makePickle
# polyglot-covers: python.logging.handlers.SocketHandler-length-prefix
# polyglot-covers: python.logging.handlers.SocketHandler-pickle-security
# polyglot-covers: python.logging.handlers.DatagramHandler
# polyglot-covers: python.logging.handlers.DatagramHandler-wire-format
# polyglot-covers: python.logging.handlers.SysLogHandler
# polyglot-covers: python.logging.handlers.SysLogHandler.encodePriority
# polyglot-covers: python.logging.handlers.SysLogHandler.mapPriority
# polyglot-covers: python.logging.handlers.syslog-custom-level-fallback

import logging
from logging.handlers import DatagramHandler
from logging.handlers import SocketHandler
from logging.handlers import SysLogHandler
import pickle
import struct

import pytest


def _record():
    return logging.makeLogRecord(
        {
            "name": "polyglot.transport",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "job=%s",
            "args": (7,),
            "exc_info": None,
        }
    )


@pytest.mark.parametrize(
    "handler_class",
    [SocketHandler, DatagramHandler],
)
def test_socket_family_pickle_has_length_prefix_and_merged_message(handler_class):
    """constructor 只保存 endpoint；不调用 emit/createSocket 就不会进行网络 I/O。"""

    handler = handler_class("example.invalid", 9020)
    try:
        payload = handler.makePickle(_record())
    finally:
        handler.close()

    declared_length = struct.unpack(">L", payload[:4])[0]
    record_dict = pickle.loads(payload[4:])

    assert declared_length == len(payload) - 4
    assert record_dict["name"] == "polyglot.transport"
    assert record_dict["msg"] == "job=7"
    assert record_dict["args"] is None
    assert record_dict["exc_info"] is None


def test_syslog_priority_combines_facility_and_severity_numbers_offline():
    """priority = facility * 8 + severity；字符串名称经标准映射后再组合。"""

    handler = object.__new__(SysLogHandler)

    expected = (SysLogHandler.LOG_LOCAL0 << 3) | SysLogHandler.LOG_INFO
    assert handler.encodePriority("local0", "info") == expected
    assert handler.encodePriority(SysLogHandler.LOG_USER, SysLogHandler.LOG_ERR) == 11
    with pytest.raises(ValueError, match="Unknown facility"):
        handler.encodePriority("missing", "info")


def test_syslog_level_mapping_falls_back_to_warning_for_custom_names():
    """未知 level name 默认映射 warning；自定义 level 应覆盖 mapPriority 才精确。"""

    handler = object.__new__(SysLogHandler)

    assert handler.mapPriority("DEBUG") == "debug"
    assert handler.mapPriority("CRITICAL") == "critical"
    assert handler.mapPriority("NOTICE") == "warning"
