# polyglot-covers: r.tooling.source-local-and-chdir-environments

local({
    root <- tempfile("polyglot-r-source-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    path <- file.path(root, "module.R")
    writeLines(c("location <- getwd()", "exported <- 42L"), path)

    module <- new.env(parent = baseenv())
    result <- source(path, local = module, chdir = TRUE)

    stopifnot(
        identical(module$exported, 42L),
        identical(normalizePath(module$location), normalizePath(root)),
        identical(result$value, 42L),
        !exists("exported", inherits = FALSE)
    )
})
