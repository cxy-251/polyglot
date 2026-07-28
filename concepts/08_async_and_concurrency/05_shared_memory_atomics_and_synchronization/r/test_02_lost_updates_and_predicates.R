# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_117_parallel_reproducible_rng_streams.R
#
# 共同问题：共享更新怎样避免丢失，等待条件怎样重新检查。
# 对照观察：PSOCK worker 各自更新副本，父进程显式归并结果；没有 condition-variable predicate API。

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
