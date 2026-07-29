# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_120_noninteractive_graphics_and_runtime_capabilities.R
#
# 共同问题：配置缺失、能力缺失和不可恢复运行时失败如何区分。
# 对照观察：R 以环境变量和 `capabilities` 做运行时检测；缺失配置应显式 `stop` 而非伪造默认成功。

require_configuration <- function(name) {
    value <- Sys.getenv(name, unset = NA_character_)
    if (is.na(value)) stop("missing configuration")
    value
}

stopifnot(
    inherits(tryCatch(require_configuration("POLYGLOT_ABSENT"), error = identity), "error"),
    is.logical(capabilities("cairo")),
    identical(length(capabilities("cairo")), 1L)
)
