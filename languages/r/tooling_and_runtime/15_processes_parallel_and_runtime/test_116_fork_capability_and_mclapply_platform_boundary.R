# polyglot-covers: r.tooling.fork-capability-and-mclapply-platform-boundary

supports_fork <- .Platform$OS.type != "windows"

if (supports_fork) {
    parent_pid <- Sys.getpid()
    results <- parallel::mclapply(1:2, function(value) {
        c(value = value * 2L, separate_process = as.integer(Sys.getpid() != parent_pid))
    }, mc.cores = 2L)
    stopifnot(
        identical(vapply(results, `[[`, integer(1), "value"), c(2L, 4L)),
        all(vapply(results, `[[`, integer(1), "separate_process") == 1L)
    )
} else {
    stopifnot(identical(parallel::mclapply(1:2, identity, mc.cores = 1L), as.list(1:2)))
}
