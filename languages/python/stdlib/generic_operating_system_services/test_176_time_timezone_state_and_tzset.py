"""176｜process-global timezone constants、``TZ``/``tzset`` 与 UTC normalization。

localtime/mktime 依赖 process-global timezone rules；仅修改 ``TZ`` 后必须调用
``tzset`` 才可移植。测试暂时切到无 DST 的 ``UTC0`` 并在 finally 恢复，避免污染
pytest process。应用处理历史时区规则时应优先使用 ``zoneinfo``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.time.tzset python.time.TZ-environment
# polyglot-covers: python.time.timezone python.time.altzone
# polyglot-covers: python.time.daylight python.time.tzname
# polyglot-covers: python.time.timezone-process-global python.time.timezone-state-restore
# polyglot-covers: python.time.localtime-utc0 python.time.mktime-local-rules

import os
import time

import pytest


def test_timezone_constants_have_platform_defined_structural_types():
    """timezone/altzone 是 UTC 以西秒数；不要误当作 east-positive UTC offset。"""

    assert type(time.timezone) is int
    assert type(time.altzone) is int
    assert type(time.daylight) is int
    assert len(time.tzname) == 2
    assert all(isinstance(name, str) for name in time.tzname)


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="平台不提供 TZ/tzset")
def test_tzset_applies_utc0_and_state_is_restored_after_case(monkeypatch):
    """UTC0 中 local/UTC conversion 一致；finally 同步恢复 C library timezone state。"""

    original = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "UTC0")
    try:
        time.tzset()

        assert time.timezone == 0
        assert time.daylight == 0
        assert time.localtime(0)[:8] == time.gmtime(0)[:8]
        assert time.mktime(time.localtime(1_600_000_000)) == 1_600_000_000
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()
