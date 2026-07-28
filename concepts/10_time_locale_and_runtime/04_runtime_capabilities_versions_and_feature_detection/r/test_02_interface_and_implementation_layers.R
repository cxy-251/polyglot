# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_119_compiler_reflection_and_runtime_observation.R
#
# 共同问题：稳定语言接口与当前实现观察怎样分层。
# 对照观察：`typeof`/`.Machine` 是公开接口；GC 数字与编译器表示只作为当次运行观察，不锁定布局或性能。

garbage_collection <- gc()
session <- sessionInfo()

stopifnot(
    identical(typeof(1), "double"),
    .Machine$double.eps > 0,
    is.matrix(garbage_collection),
    inherits(session, "sessionInfo"),
    identical(as.character(session$R.version$version.string), R.version.string)
)
