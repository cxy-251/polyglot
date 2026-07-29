# R 课程的可复现执行合同属于 harness，不计入语言知识。
commands <- Sys.which(c("R", "Rscript", "gcc", "make"))
configuration <- system2(
    file.path(R.home("bin"), "R"),
    c("CMD", "config", "CC"),
    stdout = TRUE,
    stderr = TRUE
)
base_description <- utils::packageDescription("base")
mass_description <- utils::packageDescription("MASS")
assertion_error <- tryCatch(stopifnot(FALSE), error = identity)

stopifnot(
    identical(as.character(getRversion()), "4.6.1"),
    "--vanilla" %in% commandArgs(),
    startsWith(Sys.getenv("R_USER"), "/tmp/polyglot-r-"),
    startsWith(Sys.getenv("R_LIBS_USER"), "/tmp/polyglot-r-"),
    startsWith(tempdir(), "/tmp/polyglot-r-"),
    all(nzchar(commands)),
    length(configuration) >= 1L,
    is.null(attr(configuration, "status", exact = TRUE)),
    identical(base_description$Priority, "base"),
    identical(mass_description$Priority, "recommended"),
    inherits(assertion_error, "error")
)
