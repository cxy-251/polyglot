# Current Task

ID: `python.stdlib.calendar`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `calendar` 测试套，覆盖 proleptic Gregorian 计算、按周/月/年生成结构化日历数据、文本/HTML 渲染、全局与实例 first weekday、闰年工具和 UTC time tuple 转换；明确 padding、locale 与进程全局状态边界。

## Covers

- Monday=0 到 Sunday=6 的 weekday 常量与默认周起点；
- `Calendar(firstweekday)` / `firstweekday` 属性 / `iterweekdays()` 的实例级配置；
- 模块级 `setfirstweekday()` / `firstweekday()` 的进程全局配置及恢复；
- `itermonthdates()` 返回前后月补齐的完整 `date` 周；
- `itermonthdays()` 以 `0` 表示目标月外 padding；
- `itermonthdays2()` 的 `(day, weekday)`、`itermonthdays3()` 的 `(year, month, day)`、`itermonthdays4()` 的完整四元组；
- `itermonthdays*` 不受 `datetime.date` 的 1..9999 年范围限制，展示 year 0 / negative year 的 ISO 8601 含义；
- `monthdatescalendar()` / `monthdayscalendar()` / `monthdays2calendar()` 的周矩阵结构；
- `yeardatescalendar()` / `yeardayscalendar()` / `yeardays2calendar()` 的 width 分组和 12 个月覆盖；
- `TextCalendar.formatmonth()` / `formatyear()` 与 `prmonth()` 输出边界；
- `HTMLCalendar.formatmonth()` / `formatyear()` / `formatyearpage()` 的 table/page 与 bytes encoding；
- 继承 `HTMLCalendar` 自定义 weekday/month CSS class，而不是事后替换整段 HTML；
- `LocaleTextCalendar` / `LocaleHTMLCalendar` 临时修改 process-wide locale、因而不是线程安全；只在子进程用稳定 `C` locale 演示；
- `isleap()` 的 Gregorian 规则、`leapdays(y1, y2)` 的半开区间和跨世纪情况；
- `weekday()`、`monthrange()`、`monthcalendar()` 的数值结果和 padding；
- `weekheader()`、`day_name` / `day_abbr`、`month_name` / `month_abbr` 的 current-locale 属性与 month index 0 空值；
- `timegm()` 与 `time.gmtime()` 的 UTC/POSIX 互逆关系；
- `IllegalMonthError` / `IllegalWeekdayError` 的 ValueError 边界。

## Common Pitfalls To Explain

- 混淆 `weekday()` 的 Monday=0 与 `datetime.isoweekday()` 的 Monday=1；
- 修改模块级 first weekday 后不恢复，导致其他测试的月矩阵列顺序改变；
- 把 `0` padding 当作真实日期，或误以为 `itermonthdates()` 只返回目标月；
- 假设每月固定 5 周；完整矩阵可能为 4、5 或 6 周；
- 把 `leapdays(y1, y2)` 的 y2 当作包含端点；
- 认为所有能由 `calendar` 数值迭代的年份都能构造 `datetime.date`；
- 对英文月份/星期名写跨 locale 断言；
- 在线程中使用 Locale*Calendar，忽略它临时改变进程全局 locale；
- 手工拼接/替换 HTMLCalendar 输出而不是通过 CSS class 属性定制；
- 把 `timegm()` 当本地时间转换；它明确按 UTC/POSIX 解释 tuple。

## Target File

`languages/python/stdlib/data_types/test_045_calendar_layouts.py`

## Official Sources

- https://docs.python.org/3.10/library/calendar.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- autouse fixture 快照并恢复模块级 first weekday；实例 Calendar 测试优先使用实例配置；
- locale 相关格式化只在短生命周期子进程使用 `C` locale，不修改 pytest 主进程 locale；
- 文本/HTML 不做完整大字符串快照，只断言结构、关键字段和自定义 class；
- 不断言平台相关的最早可格式化年份，也不依赖当前系统语言；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--043 已完成此前范围首轮编写；044 `zoneinfo` 已在 `data_types/` 完成首轮静态编写，真实 IANA 数据缺失会清晰 skip，全局 cache/TZPATH 操作均在子进程。全部 Python 文件仍未运行。下一步直接编写 045 `calendar`；不要先运行 pytest。
