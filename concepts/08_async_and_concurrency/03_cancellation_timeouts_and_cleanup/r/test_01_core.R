# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_116_fork_capability_and_mclapply_platform_boundary.R
#
# 共同问题：运行中的工作怎样取消，取消后谁负责回收。
# 对照观察：Unix fork job 可由进程信号终止并用 `mccollect` 回收；Windows 无对应 fork 能力。

if (.Platform$OS.type != "windows") {
    job <- parallel::mcparallel(repeat {})
    killed <- tools::pskill(job$pid, tools::SIGTERM)
    collected <- withCallingHandlers(
        parallel::mccollect(job, wait = TRUE),
        warning = function(condition) invokeRestart("muffleWarning")
    )
    stopifnot(isTRUE(killed), length(collected) == 1L, is.null(collected[[1L]]))
} else {
    stopifnot(!isTRUE(capabilities("fork")))
}
