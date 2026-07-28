# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_100_date_time_zones_and_differences.R
#
# 共同问题：duration 单位怎样转换，不同 clock 的数值能否混算。
# 对照观察：`difftime` 显式换算单位；POSIXct 是 wall-clock instant，`proc.time` 是进程计时观察。

duration <- as.difftime(2, units = "hours")
instant <- as.POSIXct("2026-01-01 00:00:00", tz = "UTC")

stopifnot(
    identical(as.numeric(duration, units = "mins"), 120),
    identical(format(instant + duration, tz = "UTC"), "2026-01-01 02:00:00"),
    inherits(instant, "POSIXct"),
    is.numeric(proc.time()[["elapsed"]])
)
