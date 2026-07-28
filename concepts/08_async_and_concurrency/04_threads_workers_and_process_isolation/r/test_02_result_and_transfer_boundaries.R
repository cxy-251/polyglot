# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_115_psock_cluster_serialization_and_process_isolation.R
#
# 共同问题：并发结果保留对象身份还是经过传输。
# 对照观察：PSOCK 结果经 serialization 返回；environment 内容可重建，但不保留父进程对象身份。

local({
    cluster <- parallel::makePSOCKcluster(1L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    source <- new.env(parent = emptyenv())
    source$value <- 42L
    parallel::clusterExport(cluster, "source", envir = environment())
    restored <- parallel::clusterCall(cluster, function() source)[[1L]]

    stopifnot(
        identical(restored$value, 42L),
        !identical(restored, source)
    )
})
