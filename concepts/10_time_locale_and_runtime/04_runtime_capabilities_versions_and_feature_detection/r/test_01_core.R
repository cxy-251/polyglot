# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_119_compiler_reflection_and_runtime_observation.R
#
# 共同问题：怎样读取结构化运行时版本、探测能力，并区分公开接口与实现观察。
# 对照观察：R 用 package_version 报告版本；`capabilities` 与 `.Platform` 检测当前实现和平台。

version <- getRversion()
session <- sessionInfo()
stopifnot(
    inherits(version, "package_version"),
    length(unclass(version)[[1L]]) >= 2L,
    identical(as.character(session$R.version$version.string), R.version.string),
    identical(typeof(1), "double"),
    .Machine$double.eps > 0,
    .Platform$OS.type %in% c("unix", "windows"),
    is.logical(capabilities("cairo")),
    identical(length(capabilities("cairo")), 1L)
)
