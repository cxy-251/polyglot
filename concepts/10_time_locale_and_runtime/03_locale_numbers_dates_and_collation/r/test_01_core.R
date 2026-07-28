# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_099_csv_encodings_locale_and_regular_expressions.R
#
# 共同问题：locale 怎样影响数字、日期和排序。
# 对照观察：格式函数可显式固定小数标记；LC_TIME/LC_COLLATE 是进程状态，测试必须恢复。

local({
    old_time <- Sys.getlocale("LC_TIME")
    on.exit(suppressWarnings(Sys.setlocale("LC_TIME", old_time)), add = TRUE)
    suppressWarnings(Sys.setlocale("LC_TIME", "C"))
    date <- as.Date("2026-07-28")

    stopifnot(
        identical(format(1.5, decimal.mark = ","), "1,5"),
        identical(format(date, "%b"), "Jul"),
        identical(sort(c("b", "a"), method = "radix"), c("a", "b"))
    )
})
