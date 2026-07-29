# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_118_parallel_error_propagation_and_worker_cleanup.R
#
# 共同问题：动态负载均衡是否改变结果顺序，worker 完成顺序能否当作事件循环观察。
# 对照观察：`clusterApplyLB` 动态分派 worker，但返回列表仍按输入位置排列，不暴露事件循环队列。

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    result <- parallel::clusterApplyLB(cluster, c(4L, 1L, 3L, 2L), function(value) {
        sum(seq_len(value))
    })

    stopifnot(
        identical(unlist(result), c(10L, 1L, 6L, 3L)),
        !exists("queueMicrotask", mode = "function")
    )
})
