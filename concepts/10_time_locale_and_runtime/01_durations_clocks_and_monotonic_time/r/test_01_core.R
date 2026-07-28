# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_100_date_time_zones_and_differences.R
#
# 共同问题：duration 与 wall clock 如何区分，经过时间怎样观察。
# 对照观察：`difftime` 携带单位；`proc.time()["elapsed"]` 适合进程内相对观察，不等同日历时间。

before <- unname(proc.time()[["elapsed"]])
sum(seq_len(1000L))
after <- unname(proc.time()[["elapsed"]])
duration <- as.difftime(90, units = "secs")

stopifnot(
    after >= before,
    inherits(duration, "difftime"),
    identical(as.numeric(duration, units = "secs"), 90)
)
