"""044｜``zoneinfo`` IANA 地区时区、DST 转换、cache 与数据源示例。

``ZoneInfo`` 提供规则引擎，但时区数据来自系统 IANA 数据库或可选 ``tzdata`` 包，
模块本身并不捆绑 transition 数据。需要真实数据的测试通过 helper 清晰 skip；不安装
额外依赖来掩盖部署环境缺少数据库的问题。

2020 年 America/Los_Angeles 的官方示例用于解释 fall-back、spring-forward 与
``fold``。会改变进程级 cache、TZPATH 或环境变量的接口全部放在子进程。当前文件
尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.zoneinfo python.zoneinfo.ZoneInfo
# polyglot-covers: python.zoneinfo.data-sources python.zoneinfo.ZoneInfoNotFoundError
# polyglot-covers: python.zoneinfo.key python.zoneinfo.string-representation
# polyglot-covers: python.zoneinfo.primary-cache python.zoneinfo.no_cache
# polyglot-covers: python.zoneinfo.clear_cache python.zoneinfo.cache-global-state
# polyglot-covers: python.zoneinfo.dst-transition python.zoneinfo.wall-time-arithmetic
# polyglot-covers: python.zoneinfo.fold python.zoneinfo.ambiguous-time
# polyglot-covers: python.zoneinfo.nonexistent-time python.zoneinfo.utc-conversion
# polyglot-covers: python.zoneinfo.from_file python.zoneinfo.pickle
# polyglot-covers: python.zoneinfo.available_timezones python.zoneinfo.TZPATH
# polyglot-covers: python.zoneinfo.reset_tzpath python.zoneinfo.PYTHONTZPATH

import os
import pickle
import subprocess
import sys
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import tzinfo
from pathlib import Path

import pytest
import zoneinfo
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError


LOS_ANGELES_KEY = "America/Los_Angeles"


def _zone_or_skip(key):
    """读取真实 IANA zone；部署没有系统/tzdata 数据时给出可诊断 skip。"""

    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError:
        pytest.skip(
            f"当前 Python 环境没有可用的 IANA zone data，无法加载 {key!r}"
        )


def _tzif_path_or_skip(key):
    """只在公开 TZPATH 中查找可读 TZif；package-only 数据不伪造文件路径。"""

    relative_parts = key.split("/")
    for directory in zoneinfo.TZPATH:
        candidate = Path(directory).joinpath(*relative_parts)
        if candidate.is_file():
            return candidate
    pytest.skip(f"TZPATH 中没有可直接读取的 TZif 文件：{key}")


def test_zoneinfo_is_tzinfo_with_a_machine_key_not_a_ui_label():
    """IANA key 适合持久化标识；本地化城市名称应由 CLDR 等展示层提供。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)

    assert isinstance(los_angeles, tzinfo)
    assert los_angeles.key == LOS_ANGELES_KEY
    assert str(los_angeles) == LOS_ANGELES_KEY

    summer = datetime(2020, 7, 1, 12, tzinfo=los_angeles)
    assert summer.tzname() == "PDT"
    assert summer.tzname() != los_angeles.key


def test_missing_zone_error_is_a_key_error_subclass():
    """规范合法但不存在的 key 抛 ZoneInfoNotFoundError，可按配置键缺失处理。"""

    assert issubclass(ZoneInfoNotFoundError, KeyError)

    with pytest.raises(ZoneInfoNotFoundError):
        ZoneInfo("Etc/Polyglot_Definitely_Missing_Zone")


@pytest.mark.parametrize(
    "invalid_key",
    ["/UTC", "../UTC", "America/../UTC", ""],
)
def test_zone_key_must_be_a_normalized_relative_posix_path(invalid_key):
    """ZoneInfo key 不是任意文件路径；绝对路径、上级跳转和空 key 都被拒绝。"""

    with pytest.raises(ValueError):
        ZoneInfo(invalid_key)


def test_primary_constructor_returns_one_cached_identity_per_key():
    """主构造器使用进程 cache；同一 key 不只是相等，而是同一个对象。"""

    first = _zone_or_skip(LOS_ANGELES_KEY)
    second = ZoneInfo(LOS_ANGELES_KEY)

    assert first is second


def test_no_cache_constructor_returns_fresh_zone_objects():
    """no_cache 绕过 identity cache；除测试/特殊反序列化策略外通常不需要它。"""

    _zone_or_skip(LOS_ANGELES_KEY)
    first = ZoneInfo.no_cache(LOS_ANGELES_KEY)
    second = ZoneInfo.no_cache(LOS_ANGELES_KEY)
    primary = ZoneInfo(LOS_ANGELES_KEY)

    assert first is not second
    assert first is not primary
    assert second is not primary
    assert first.key == second.key == primary.key == LOS_ANGELES_KEY


def test_region_zone_changes_offset_and_name_across_fall_transition():
    """地区时区与固定 -08:00 不同：夏季为 PDT，fall-back 后才回到 PST。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)
    before = datetime(2020, 10, 31, 12, tzinfo=los_angeles)
    after = before + timedelta(days=1)

    assert before.utcoffset() == timedelta(hours=-7)
    assert before.tzname() == "PDT"
    assert after == datetime(2020, 11, 1, 12, tzinfo=los_angeles)
    assert after.utcoffset() == timedelta(hours=-8)
    assert after.tzname() == "PST"

    fixed_pst = timezone(timedelta(hours=-8), "PST-fixed")
    assert before.utcoffset() != datetime(2020, 7, 1, tzinfo=fixed_pst).utcoffset()


def test_one_wall_clock_day_across_fall_back_is_25_hours_on_the_utc_timeline():
    """同 tzinfo 的 datetime 加减按墙上字段；真实 elapsed time 要先转换到 UTC。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)
    before = datetime(2020, 10, 31, 12, tzinfo=los_angeles)
    after = before + timedelta(days=1)

    # tzinfo identity 相同时，datetime subtraction 忽略 offset 变化。
    assert after - before == timedelta(days=1)

    utc_elapsed = after.astimezone(timezone.utc) - before.astimezone(timezone.utc)
    assert utc_elapsed == timedelta(hours=25)


def test_fold_selects_the_two_instants_in_a_repeated_fall_back_hour():
    """01:30 出现两次；fold=0 选转换前 PDT，fold=1 选转换后 PST。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)
    earlier = datetime(2020, 11, 1, 1, 30, tzinfo=los_angeles, fold=0)
    later = earlier.replace(fold=1)

    assert earlier.utcoffset() == timedelta(hours=-7)
    assert earlier.tzname() == "PDT"
    assert later.utcoffset() == timedelta(hours=-8)
    assert later.tzname() == "PST"
    assert later.timestamp() - earlier.timestamp() == 3_600

    # 相同 tzinfo 的墙上时间比较会忽略 fold；要区分时刻应比较 timestamp/UTC。
    assert earlier == later
    assert later - earlier == timedelta(0)
    assert earlier.astimezone(timezone.utc) != later.astimezone(timezone.utc)


def test_conversion_from_utc_sets_fold_for_the_repeated_hour_automatically():
    """从确定时刻转换没有歧义，ZoneInfo 能自动标记重复小时的早/晚实例。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)
    before_transition_utc = datetime(2020, 11, 1, 8, tzinfo=timezone.utc)
    after_transition_utc = before_transition_utc + timedelta(hours=1)

    earlier = before_transition_utc.astimezone(los_angeles)
    later = after_transition_utc.astimezone(los_angeles)

    assert earlier.replace(tzinfo=None) == datetime(2020, 11, 1, 1)
    assert later.replace(tzinfo=None) == datetime(2020, 11, 1, 1)
    assert earlier.fold == 0
    assert earlier.utcoffset() == timedelta(hours=-7)
    assert later.fold == 1
    assert later.utcoffset() == timedelta(hours=-8)


def test_nonexistent_spring_forward_wall_time_is_not_rejected_on_construction():
    """02:30 从未发生，但直接附加 ZoneInfo 不验证 wall time；fold 选择 gap 两侧规则。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)
    gap_before_rule = datetime(
        2020,
        3,
        8,
        2,
        30,
        tzinfo=los_angeles,
        fold=0,
    )
    gap_after_rule = gap_before_rule.replace(fold=1)

    assert gap_before_rule.utcoffset() == timedelta(hours=-8)
    assert gap_after_rule.utcoffset() == timedelta(hours=-7)

    # 不存在的墙上字段无法经 UTC 往返保持原值，可据此做业务层有效性检查。
    original_wall_time = datetime(2020, 3, 8, 2, 30)
    for candidate in (gap_before_rule, gap_after_rule):
        round_trip = candidate.astimezone(timezone.utc).astimezone(los_angeles)
        assert round_trip.replace(tzinfo=None) != original_wall_time


def test_ordinary_aware_datetime_round_trips_between_zone_and_utc():
    """非 transition 时刻可以通过 UTC、timestamp 稳定往返，并保持同一 instant。"""

    los_angeles = _zone_or_skip(LOS_ANGELES_KEY)
    local = datetime(2020, 6, 1, 9, 15, tzinfo=los_angeles)
    utc = local.astimezone(timezone.utc)

    assert utc == datetime(2020, 6, 1, 16, 15, tzinfo=timezone.utc)
    assert utc.astimezone(los_angeles) == local
    assert datetime.fromtimestamp(local.timestamp(), los_angeles) == local


def test_primary_zone_pickles_by_key_and_rejoins_the_primary_cache():
    """pickle 不保存 transition 表；反序列化按 key 在当前环境重新查数据。"""

    primary = _zone_or_skip(LOS_ANGELES_KEY)
    restored = pickle.loads(pickle.dumps(primary))

    assert restored.key == LOS_ANGELES_KEY
    assert restored is primary
    assert restored is ZoneInfo(LOS_ANGELES_KEY)


def test_no_cache_zone_pickle_keeps_bypassing_the_primary_cache():
    """no_cache 构造来源会写入 pickle 协议，恢复后仍得到独立 ZoneInfo identity。"""

    _zone_or_skip(LOS_ANGELES_KEY)
    primary = ZoneInfo(LOS_ANGELES_KEY)
    uncached = ZoneInfo.no_cache(LOS_ANGELES_KEY)
    restored = pickle.loads(pickle.dumps(uncached))

    assert restored.key == LOS_ANGELES_KEY
    assert restored is not uncached
    assert restored is not primary


def test_from_file_reads_an_existing_tzif_but_is_not_cached_or_picklable():
    """from_file 面向显式 TZif 流；package-only 环境找不到真实文件时跳过。"""

    path = _tzif_path_or_skip(LOS_ANGELES_KEY)
    primary = _zone_or_skip(LOS_ANGELES_KEY)

    with path.open("rb") as tzif:
        from_file = ZoneInfo.from_file(tzif, key=LOS_ANGELES_KEY)

    assert from_file.key == LOS_ANGELES_KEY
    assert str(from_file) == LOS_ANGELES_KEY
    assert from_file is not primary

    sample = datetime(2020, 7, 1, 12)
    assert sample.replace(tzinfo=from_file).utcoffset() == sample.replace(
        tzinfo=primary,
    ).utcoffset()

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(from_file)


def test_available_timezones_returns_canonical_keys_without_snapshotting_them():
    """结果取决于部署数据且每次重算；只验证集合契约，不保存庞大易变快照。"""

    keys = zoneinfo.available_timezones()

    assert isinstance(keys, set)
    assert all(isinstance(key, str) and key for key in keys)
    assert all(not key.startswith(("posix/", "right/")) for key in keys)

    try:
        ZoneInfo(LOS_ANGELES_KEY)
    except ZoneInfoNotFoundError:
        pass
    else:
        assert LOS_ANGELES_KEY in keys

    # 此函数为识别 TZif 可能打开大量文件，不应放在请求热路径反复调用。


def test_tzpath_is_read_dynamically_and_contains_only_absolute_paths():
    """不要 ``from zoneinfo import TZPATH`` 后长期缓存；reset 时模块属性会换对象。"""

    assert isinstance(zoneinfo.TZPATH, tuple)
    assert all(os.path.isabs(path) for path in zoneinfo.TZPATH)


def test_clear_cache_effect_is_demonstrated_in_an_isolated_process():
    """clear_cache 会改变进程 identity/语义；子进程结束即丢弃该全局变更。"""

    program = f'''
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

key = {LOS_ANGELES_KEY!r}
try:
    first = ZoneInfo(key)
except ZoneInfoNotFoundError:
    print("zone-data-unavailable")
else:
    assert ZoneInfo(key) is first
    ZoneInfo.clear_cache(only_keys=[key])
    replacement = ZoneInfo(key)
    assert replacement is not first
    assert ZoneInfo(key) is replacement
    print("isolated-cache-clear-ok")
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    result = completed.stdout.strip()
    if result == "zone-data-unavailable":
        pytest.skip("子进程没有可用 IANA zone data")
    assert result == "isolated-cache-clear-ok"


def test_reset_tzpath_validation_and_cache_behavior_are_process_isolated():
    """reset_tzpath 不清已有 cache；参数必须是绝对路径组成的非字符串 sequence。"""

    program = f'''
import os
import zoneinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

original_path = zoneinfo.TZPATH
imported_snapshot = zoneinfo.TZPATH
key = {LOS_ANGELES_KEY!r}

try:
    cached = ZoneInfo(key)
except ZoneInfoNotFoundError:
    cached = None

zoneinfo.reset_tzpath(())
assert zoneinfo.TZPATH == ()
assert imported_snapshot == original_path
if cached is not None:
    assert ZoneInfo(key) is cached

try:
    zoneinfo.reset_tzpath(("relative/path",))
except ValueError:
    pass
else:
    raise AssertionError("relative TZPATH component should fail")

try:
    zoneinfo.reset_tzpath("/tmp")
except TypeError:
    pass
else:
    raise AssertionError("a string is not a TZPATH sequence")

zoneinfo.reset_tzpath(original_path)
assert all(os.path.isabs(path) for path in zoneinfo.TZPATH)
print("isolated-tzpath-reset-ok")
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "isolated-tzpath-reset-ok"


def test_empty_python_tzpath_environment_is_applied_only_in_a_child_process():
    """PYTHONTZPATH='' 会忽略系统搜索目录；tzdata package 若存在仍可作为 fallback。"""

    program = """
import zoneinfo

assert zoneinfo.TZPATH == ()
print("empty-python-tzpath-ok")
"""
    environment = dict(os.environ)
    environment["PYTHONTZPATH"] = ""

    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.stdout.strip() == "empty-python-tzpath-ok"
