# Current Task

ID: `python.stdlib.datetime-core`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `datetime` 核心测试套，系统展示 `timedelta`、`date`、`time`、`datetime`、`timezone` 的构造、规范化、算术、比较、ISO/格式化和时间戳转换；重点讲清 naive/aware 边界、固定偏移时区、日期算术与时刻算术的区别。IANA 时区和 DST 转换留给下一份 `zoneinfo` 测试套。

## Covers

- `MINYEAR` / `MAXYEAR`、各类型的 `min` / `max` / `resolution`，以及不可变、可哈希属性；
- `timedelta` 将 weeks/days/hours/minutes/seconds/milliseconds/microseconds 规范化为 days/seconds/microseconds；
- 负 `timedelta` 的规范化表示、`total_seconds()` 与 `.seconds` 的差别；
- `timedelta` 加减、正负号、`abs()`、整数/浮点乘除、与另一个 duration 的 `/`、`//`、`%`、`divmod()`；
- `date` 构造范围和闰年校验；
- `date.fromordinal()` / `toordinal()`、`fromisoformat()` / `isoformat()` 的往返；
- `weekday()` / `isoweekday()` / `isocalendar()` / `fromisocalendar()`，包括 Gregorian 年与 ISO week-year 不一致的年界；
- `date.replace()`、`timetuple()` 和 date ± timedelta；
- date 算术只使用 `timedelta.days`，忽略 seconds/microseconds；
- `time` 的字段、`fold`、`replace()`、`isoformat(timespec=...)`，以及 time 本身不支持跨日算术；
- `datetime` 构造、`combine()`、`date()`、`time()`、`timetz()`、`replace()`；
- datetime ± timedelta、datetime 相减和字段跨日进位；
- naive 对象的 `tzinfo is None`，aware 对象的 `utcoffset()` 非 `None`；
- naive 与 aware datetime 不能排序或相减；相等比较返回不相等而不是推测本地时区；
- `timezone.utc`、固定偏移 `timezone()`、`utcoffset()` / `tzname()` / `dst()`；
- `astimezone()` 保持同一时刻，`replace(tzinfo=...)` 只是重新贴标签；
- `timestamp()` 与 `fromtimestamp(timestamp, tz=...)` 的 aware 往返；
- `datetime.utcnow()` 返回 naive UTC，而 `datetime.now(timezone.utc)` 返回 aware UTC；只断言形状，不依赖真实当前时间；
- `isoformat()` / `fromisoformat()` 的 Python 3.10 支持范围、separator 与 `timespec`；
- `strftime()` / `strptime()` 常用字段、缺省年份 1900 和 `%z` aware 解析；
- 无效日期、越界 fixed offset、混合 aware/naive 运算和不完整解析的异常边界。

## Common Pitfalls To Explain

- 把 `timedelta.seconds` 当作总秒数，导致跨天或负 duration 计算错误；
- 被负 timedelta 的 `days=-1, seconds=...` 规范化表示误导；
- 认为 date 加几个小时会改变日期，忽略 date 算术只看整天分量；
- 混用 naive 与 aware datetime，或把 naive 自动解释成本地/UTC 时刻；
- 用 `replace(tzinfo=...)` 做时区转换，实际只改变标签；
- 用无 `tz` 的 `fromtimestamp()` / `timestamp()` 编写依赖主机本地时区的测试；
- 把固定偏移 `timezone` 当作包含 DST 历史规则的地区时区；
- 认为 `datetime.utcnow()` 返回带 UTC tzinfo 的 aware 对象；
- 认为 Python 3.10 `fromisoformat()` 接受所有 ISO 8601 变体或结尾 `Z`；
- 解析不含年份的月日后忘记 `strptime()` 默认使用 1900，导致 2 月 29 日失败；
- 假设所有平台支持同一套非标准 `strftime` 指令。

## Target File

`languages/python/stdlib/data_types/test_043_datetime_core.py`

## Official Sources

- https://docs.python.org/3.10/library/datetime.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 不读取系统本地时区、不修改 `TZ`、不 sleep，不对真实当前时间写精确值断言；
- 稳定时刻示例使用 `timezone.utc` 或显式 fixed offset；
- `zoneinfo`、DST gap/fold 和 IANA 数据库可用性留到后续独立文件；
- 平台相关 `strftime` 行为只使用 Python 3.10 文档保证的常用指令；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--041 已完成语言、内置层、文本/文件访问和 `struct` 首轮编写；042 `codecs` 已在 `binary_data/` 完成首轮静态编写。全部 Python 文件仍未运行。下一步创建 `data_types/` 并直接编写 043 `datetime` 核心；不要先运行 pytest。
