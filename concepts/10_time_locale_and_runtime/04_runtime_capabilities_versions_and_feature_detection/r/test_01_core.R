# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_120_noninteractive_graphics_and_runtime_capabilities.R
#
# 共同问题：怎样精确检查运行时版本并探测平台能力。
# 对照观察：R 用 `getRversion`/`R.version` 报告版本，`capabilities` 与 `.Platform` 做运行时检测。

stopifnot(
    identical(as.character(getRversion()), "4.6.1"),
    identical(R.version$major, "4"),
    identical(.Platform$OS.type, "unix"),
    is.logical(capabilities("cairo")),
    identical(length(capabilities("cairo")), 1L)
)
