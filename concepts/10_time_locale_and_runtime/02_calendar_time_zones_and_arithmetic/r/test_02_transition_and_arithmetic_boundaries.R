# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_100_date_time_zones_and_differences.R
#
# 共同问题：DST transition 与固定秒数算术怎样区分。
# 对照观察：POSIXct 加 3600 是 instant 算术；可用 Olson zone 格式化观察本地时钟跳变。

zone <- "America/New_York"
if (zone %in% OlsonNames()) {
    before <- as.POSIXct("2024-03-10 01:30:00", tz = zone)
    after <- before + 3600
    stopifnot(
        identical(format(before, "%H:%M", tz = zone), "01:30"),
        identical(format(after, "%H:%M", tz = zone), "03:30"),
        identical(as.numeric(difftime(after, before, units = "secs")), 3600)
    )
} else {
    stopifnot(!zone %in% OlsonNames())
}
