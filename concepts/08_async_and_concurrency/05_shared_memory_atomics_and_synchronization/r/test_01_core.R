# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_115_psock_cluster_serialization_and_process_isolation.R
#
# 共同问题：并发单元怎样共享可变内存，原子操作和同步原语在哪里。
# 对照观察：标准 PSOCK 模型没有共享 R heap 或语言级 atomic；同步发生在消息发送和结果收集边界。

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    parallel::clusterEvalQ(cluster, counter <- 0L)
    result <- parallel::clusterCall(cluster, function() {
        counter <<- counter + 1L
        counter
    })

    stopifnot(identical(result, list(1L, 1L)))
})
