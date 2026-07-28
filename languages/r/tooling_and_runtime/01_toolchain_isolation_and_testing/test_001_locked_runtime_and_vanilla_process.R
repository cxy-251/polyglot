# polyglot-covers: r.tooling.locked-runtime-and-vanilla-process

stopifnot(
    identical(as.character(getRversion()), "4.6.1"),
    "--vanilla" %in% commandArgs(),
    startsWith(Sys.getenv("R_USER"), "/tmp/polyglot-r-"),
    startsWith(Sys.getenv("R_LIBS_USER"), "/tmp/polyglot-r-"),
    startsWith(tempdir(), "/tmp/polyglot-r-")
)
