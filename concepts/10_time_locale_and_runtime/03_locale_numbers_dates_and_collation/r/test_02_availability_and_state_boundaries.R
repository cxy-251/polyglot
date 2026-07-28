# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/r/tooling_and_runtime/01_toolchain_isolation_and_testing/
# polyglot-related+: test_004_options_environment_and_working_directory_cleanup.R
#
# 共同问题：请求的 locale 不可用怎样表达，修改范围如何恢复。
# 对照观察：`Sys.setlocale` 对不可用 locale 返回空字符串并警告；locale 是进程级状态。

local({
    original <- Sys.getlocale("LC_TIME")
    on.exit(suppressWarnings(Sys.setlocale("LC_TIME", original)), add = TRUE)
    unavailable <- suppressWarnings(Sys.setlocale("LC_TIME", "polyglot_INVALID_LOCALE"))

    stopifnot(
        identical(unavailable, ""),
        identical(Sys.getlocale("LC_TIME"), original)
    )
})
