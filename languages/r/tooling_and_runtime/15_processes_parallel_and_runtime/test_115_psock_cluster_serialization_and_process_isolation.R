# polyglot-covers: r.tooling.psock-process-isolation-serialization-and-rng-streams

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    parent_pid <- Sys.getpid()
    environments <- parallel::clusterCall(cluster, function() {
        list(pid = Sys.getpid(), value = 42L, global = exists("parent_pid", .GlobalEnv))
    })
    parallel::clusterSetRNGStream(cluster, iseed = 2026)
    first <- parallel::clusterCall(cluster, runif, 3L)
    parallel::clusterSetRNGStream(cluster, iseed = 2026)
    second <- parallel::clusterCall(cluster, runif, 3L)

    stopifnot(
        length(environments) == 2L,
        all(vapply(environments, function(x) x$pid != parent_pid, logical(1))),
        all(vapply(environments, function(x) identical(x$value, 42L), logical(1))),
        !any(vapply(environments, function(x) x$global, logical(1))),
        identical(first, second),
        !identical(first[[1L]], first[[2L]])
    )
})

# PSOCK worker 是独立 R process，参数与结果越过 serialization 边界；clusterSetRNGStream
# 为各 worker 建立可复现但彼此不同的 L'Ecuyer stream。
