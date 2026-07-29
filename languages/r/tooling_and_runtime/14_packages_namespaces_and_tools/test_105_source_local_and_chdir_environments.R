# polyglot-covers: r.tooling.source-environments-return-values-and-chdir

local({
    root <- tempfile("polyglot-r-source-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    path <- file.path(root, "module.R")
    writeLines(c("location <- getwd()", "exported <- 42L"), path)

    module <- new.env(parent = baseenv())
    result <- source(path, local = module, chdir = TRUE)
    isolated <- new.env(parent = baseenv())
    sys.source(path, envir = isolated, chdir = FALSE)

    stopifnot(
        identical(module$exported, 42L),
        identical(normalizePath(module$location), normalizePath(root)),
        identical(result$value, 42L),
        identical(isolated$exported, 42L),
        identical(normalizePath(isolated$location), normalizePath(getwd())),
        !exists("exported", inherits = FALSE)
    )
})

# source 返回最后一个值并可临时切换 cwd；sys.source 只在显式 environment 中求值。
