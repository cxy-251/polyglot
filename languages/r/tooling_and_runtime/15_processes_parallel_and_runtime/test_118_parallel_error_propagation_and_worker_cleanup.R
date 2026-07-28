# polyglot-covers: r.tooling.parallel-error-propagation-and-worker-cleanup

local({
    cluster <- parallel::makePSOCKcluster(1L)
    stopped <- FALSE
    on.exit({
        if (!stopped) parallel::stopCluster(cluster)
    }, add = TRUE)

    error <- tryCatch(
        parallel::clusterCall(cluster, function() stop("worker failure")),
        error = identity
    )
    parallel::stopCluster(cluster)
    stopped <- TRUE

    stopifnot(
        inherits(error, "error"),
        grepl("worker failure", conditionMessage(error), fixed = TRUE)
    )
})
