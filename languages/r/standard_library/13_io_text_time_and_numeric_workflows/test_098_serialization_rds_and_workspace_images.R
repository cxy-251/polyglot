# polyglot-covers: r.standard-library.serialization-rds-and-workspace-images

local({
    root <- tempfile("polyglot-r-serialization-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    value <- list(numbers = 1:3, label = "R", missing = NA_real_)
    rds_path <- file.path(root, "value.rds")
    workspace_path <- file.path(root, "workspace.RData")
    saveRDS(value, rds_path, version = 3)

    first <- 1L
    second <- "two"
    save(first, second, file = workspace_path, version = 3)
    restored <- new.env(parent = emptyenv())
    loaded_names <- load(workspace_path, envir = restored)

    stopifnot(
        identical(readRDS(rds_path), value),
        identical(sort(loaded_names), c("first", "second")),
        identical(restored$first, 1L),
        identical(restored$second, "two")
    )
})
