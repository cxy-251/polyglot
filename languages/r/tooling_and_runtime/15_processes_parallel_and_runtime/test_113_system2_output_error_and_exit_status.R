# polyglot-covers: r.tooling.system2-output-error-and-exit-status

success <- system2(
    file.path(R.home("bin"), "Rscript"),
    c("--vanilla", "-e", shQuote("cat('ok')")),
    stdout = TRUE,
    stderr = TRUE
)
failure <- suppressWarnings(system2(
    file.path(R.home("bin"), "Rscript"),
    c("--vanilla", "-e", shQuote("quit(status = 7L)")),
    stdout = TRUE,
    stderr = TRUE
))

stopifnot(
    identical(success, "ok"),
    is.null(attr(success, "status", exact = TRUE)),
    identical(attr(failure, "status", exact = TRUE), 7L)
)
