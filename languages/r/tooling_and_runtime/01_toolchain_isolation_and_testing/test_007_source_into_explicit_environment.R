# polyglot-covers: r.tooling.source-into-explicit-environment

local({
    source_file <- tempfile("polyglot-r-source-", fileext = ".R")
    on.exit(unlink(source_file), add = TRUE)
    writeLines(c("answer <- 42L", "double <- function(value) value * 2L"), source_file)

    sandbox <- new.env(parent = baseenv())
    sys.source(source_file, envir = sandbox)

    stopifnot(
        identical(sandbox$answer, 42L),
        identical(sandbox$double(3L), 6L),
        !exists("answer", envir = environment(), inherits = FALSE)
    )
})
