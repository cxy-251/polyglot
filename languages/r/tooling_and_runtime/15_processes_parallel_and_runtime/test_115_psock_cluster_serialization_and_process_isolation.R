# polyglot-covers: r.tooling.psock-cluster-serialization-and-process-isolation

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)
    parent_pid <- Sys.getpid()
    environments <- parallel::clusterCall(cluster, function() {
        list(pid = Sys.getpid(), value = 42L, global = exists("parent_pid", .GlobalEnv))
    })

    stopifnot(
        length(environments) == 2L,
        all(vapply(environments, function(x) x$pid != parent_pid, logical(1))),
        all(vapply(environments, function(x) identical(x$value, 42L), logical(1))),
        !any(vapply(environments, function(x) x$global, logical(1)))
    )
})
