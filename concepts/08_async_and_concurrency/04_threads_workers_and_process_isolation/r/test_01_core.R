# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_115_psock_cluster_serialization_and_process_isolation.R
#
# 共同问题：并发单元共享地址空间还是隔离进程。
# 对照观察：PSOCK worker 是独立 R 进程；父进程变量不会隐式出现，PID 也不同。

local({
    parent_value <- 42L
    parent_pid <- Sys.getpid()
    cluster <- parallel::makePSOCKcluster(1L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    observed <- parallel::clusterCall(cluster, function() {
        c(
            separate_pid = as.integer(Sys.getpid()),
            has_parent_value = as.integer(exists("parent_value", .GlobalEnv))
        )
    })[[1L]]

    stopifnot(observed[["separate_pid"]] != parent_pid, observed[["has_parent_value"]] == 0L)
})
