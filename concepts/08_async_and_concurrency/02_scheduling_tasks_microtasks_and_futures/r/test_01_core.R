# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_115_psock_cluster_serialization_and_process_isolation.R
#
# 共同问题：任务怎样调度，结果顺序由提交还是完成决定。
# 对照观察：base R 没有 microtask/future queue；`clusterApply` 将工作发给进程并按输入位置组装结果。

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    result <- parallel::clusterApply(cluster, 1:4, function(value) {
        list(value = value, pid = Sys.getpid())
    })

    stopifnot(
        identical(vapply(result, `[[`, integer(1), "value"), 1:4),
        length(unique(vapply(result, `[[`, integer(1), "pid"))) == 2L
    )
})
