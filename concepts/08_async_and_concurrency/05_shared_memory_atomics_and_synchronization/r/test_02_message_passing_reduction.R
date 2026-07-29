# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_115_psock_cluster_serialization_and_process_isolation.R
#
# 共同问题：没有共享 heap 时怎样组合并发更新，等待条件是否有语言级协议。
# 对照观察：PSOCK worker 返回独立 partial，父进程显式归并；base R 没有 condition-variable predicate API。

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    partials <- parallel::parLapply(cluster, split(1:10, rep(1:2, each = 5)), sum)
    total <- Reduce(`+`, partials, init = 0L)

    stopifnot(
        identical(total, 55L),
        identical(partials, list(`1` = 15L, `2` = 40L))
    )
})
