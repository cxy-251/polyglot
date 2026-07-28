# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_115_psock_cluster_serialization_and_process_isolation.R
#
# 共同问题：异步工作怎样返回值或传播错误。
# 对照观察：base R 没有 async/await；`parallel` 以 worker 进程和阻塞式收集返回序列化结果。

local({
    cluster <- parallel::makePSOCKcluster(1L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    result <- parallel::clusterCall(cluster, function(value) value * 2L, 21L)
    error <- tryCatch(
        parallel::clusterCall(cluster, function() stop("worker error")),
        error = identity
    )

    stopifnot(identical(result, list(42L)), inherits(error, "error"))
})
