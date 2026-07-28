# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/r/tooling_and_runtime/01_toolchain_isolation_and_testing/
# polyglot-related+: test_001_locked_runtime_and_vanilla_process.R
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
