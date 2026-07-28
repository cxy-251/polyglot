# polyglot-covers: r.tooling.parallel-reproducible-rng-streams

local({
    cluster <- parallel::makePSOCKcluster(2L)
    on.exit(parallel::stopCluster(cluster), add = TRUE)

    parallel::clusterSetRNGStream(cluster, iseed = 2026)
    first <- parallel::clusterCall(cluster, runif, 3L)
    parallel::clusterSetRNGStream(cluster, iseed = 2026)
    second <- parallel::clusterCall(cluster, runif, 3L)

    stopifnot(
        identical(first, second),
        !identical(first[[1L]], first[[2L]]),
        all(vapply(first, length, integer(1)) == 3L)
    )
})
