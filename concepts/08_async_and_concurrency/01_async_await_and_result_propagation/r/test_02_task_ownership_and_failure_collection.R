# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_118_parallel_error_propagation_and_worker_cleanup.R
#
# 共同问题：谁拥有并发任务，多个失败怎样收集。
# 对照观察：cluster 生命周期由创建者显式停止；要保留多个失败，可让每个 worker 返回 condition 数据。

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    results <- parallel::parLapply(cluster, c("first", "second"), function(label) {
        tryCatch(stop(label), error = identity)
    })

    stopifnot(
        all(vapply(results, inherits, logical(1), "error")),
        identical(vapply(results, conditionMessage, ""), c("first", "second"))
    )
})
