# polyglot-covers: r.tooling.r-cmd-compiler-and-build-tools

commands <- Sys.which(c("R", "Rscript", "gcc", "make"))
configuration <- system2(
    file.path(R.home("bin"), "R"),
    c("CMD", "config", "CC"),
    stdout = TRUE,
    stderr = TRUE
)

stopifnot(
    all(nzchar(commands)),
    identical(basename(R.home()), "R"),
    length(configuration) >= 1L,
    identical(attr(configuration, "status"), NULL)
)
