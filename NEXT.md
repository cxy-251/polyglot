# Current Task

ID: `python.stdlib.zoneinfo`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `zoneinfo` 测试套，以稳定的 2020 年 America/Los_Angeles DST 转换展示 IANA 地区时区、ambiguous/nonexistent wall time、`fold` 和 UTC 转换；同时覆盖数据源缺失、key/cache/pickle/TZPATH 契约，并严格隔离会改变进程全局路径或 cache 的示例。

## Covers

- `ZoneInfo` 是 `tzinfo` 具体实现，`key` / `str()` 表示 IANA 主键而非用户友好名称；
- 数据来自系统 IANA 数据库或可选 `tzdata` 包，标准库模块自身不捆绑时区数据；
- 数据完全缺失时 `ZoneInfoNotFoundError`，并确认它是 `KeyError` 子类；
- 主构造器 `ZoneInfo(key)` 对同一 key 使用 identity cache；
- `ZoneInfo.no_cache(key)` 每次返回新对象及其语义警告；
- `ZoneInfo.clear_cache(only_keys=...)` 的全局影响，放在短生命周期子进程演示；
- 2020-10-31 到 2020-11-01 America/Los_Angeles 从 PDT 到 PST 的 offset/name 变化；
- 跨 DST 的 `datetime + timedelta(days=1)` 保持墙上时间，但换算到 UTC 后实际 elapsed time 可为 25 小时；
- fall-back 重复的 01:00/01:30：`fold=0` 使用转换前 offset，`fold=1` 使用转换后 offset；
- 从 UTC `astimezone()` 到重复区间会自动设置正确 `fold`；
- spring-forward 不存在的墙上时间不会因直接构造而自动报错；两个 `fold` 值选择转换两侧 offset，调用方仍要做业务有效性校验；
- aware datetime 在不同 ZoneInfo/UTC 间的相等、timestamp 和往返；
- key 必须是规范化相对 POSIX path，绝对路径、`..` 等非法 key 抛 `ValueError`；
- `ZoneInfo.from_file()` 从二进制 TZif 文件创建新对象、可选 key、绕过 cache 且不可 pickle；若只有 package 数据而无可访问系统文件则清晰 skip；
- 主构造对象按 key pickle，反序列化通常回到主 cache identity；
- `no_cache` 对象 pickle 后仍绕过 cache；
- `available_timezones()` 返回当前数据源中的 canonical key set，并说明每次调用可能打开很多文件；
- `TZPATH` 只含绝对路径且应通过 `zoneinfo.TZPATH` 动态读取；
- `reset_tzpath()` 要求绝对路径 sequence、不会自动清 ZoneInfo cache；路径修改示例放在子进程隔离。

## Common Pitfalls To Explain

- 认为导入 `zoneinfo` 就保证机器一定有 IANA 数据；
- 把 `America/Los_Angeles` 这样的 key 或 `PST` 缩写直接当作本地化 UI 文案；
- 用固定 `timezone(-08:00)` 代替包含历史/DST 规则的地区 ZoneInfo；
- 认为 timedelta(days=1) 跨 DST 永远等于 UTC 时间线上的 24 小时；
- 在 fall-back 重复时间忽略 `fold`，或认为直接构造 wall time 能自动判断用户想要哪个时刻；
- 认为 spring-forward gap 中的 wall time 构造会失败；
- 随意调用 `clear_cache()` / `reset_tzpath()`，改变其他测试或长寿命 datetime 的语义；
- 认为 `reset_tzpath()` 会使已经 cache 的 key 自动重载；
- pickle transition 数据本身；实际按 key 恢复，结果依赖反序列化环境的时区数据库版本；
- 对未来政治规则、所有平台的 zone 集合或缩写写脆弱断言。

## Target File

`languages/python/stdlib/data_types/test_044_zoneinfo_transitions.py`

## Official Sources

- https://docs.python.org/3.10/library/zoneinfo.html
- https://docs.python.org/3.10/library/datetime.html#datetime.datetime.fold

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；不得安装 `tzdata` 依赖；
- helper 捕获 `ZoneInfoNotFoundError` 并对需要真实 zone data 的案例给出清晰 skip；
- 转换断言使用文档中的稳定 2020 America/Los_Angeles 历史区间，不依赖当前/未来时刻；
- `clear_cache()`、`reset_tzpath()` 和环境变量路径操作只能在子进程内演示；
- `from_file()` 只读取 `zoneinfo.TZPATH` 下现有 TZif 文件，不修改系统数据；找不到文件则 skip；
- 不把完整 `available_timezones()` 集合或时区缩写排序写成快照；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--042 已完成此前范围首轮编写；043 `datetime` 核心已在新分类 `data_types/` 完成首轮静态编写。全部 Python 文件仍未运行。下一步直接编写 044 `zoneinfo`；所有全局 cache/path 改动必须放在子进程，不要先运行 pytest。
