# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_100_date_time_zones_and_differences.R
#
# 共同问题：日历日期、时区 instant 和算术怎样表达。
# 对照观察：Date 按日计数，POSIXct 按秒表示 instant；格式化时显式选择时区。

date <- as.Date("2026-07-28")
instant <- as.POSIXct("2026-07-28 12:00:00", tz = "UTC")

stopifnot(
    identical(date + 1L, as.Date("2026-07-29")),
    identical(format(instant, tz = "UTC"), "2026-07-28 12:00:00"),
    identical(format(instant, tz = "Asia/Shanghai"), "2026-07-28 20:00:00"),
    identical(as.numeric(difftime(instant + 60, instant, units = "secs")), 60)
)
