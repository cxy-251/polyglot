# polyglot-covers: r.standard-library.file-paths-processes-and-environment

local({
    root <- tempfile("polyglot-r-files-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    nested <- file.path(root, "nested")
    dir.create(nested)
    path <- file.path(nested, "value.txt")
    writeLines("content", path, useBytes = TRUE)
    output <- system2(
        file.path(R.home("bin"), "Rscript"),
        c("--vanilla", "-e", shQuote("cat(Sys.getenv('POLYGLOT_CHILD'))")),
        stdout = TRUE,
        env = "POLYGLOT_CHILD=isolated"
    )

    stopifnot(
        identical(readLines(path, warn = FALSE), "content"),
        identical(normalizePath(dirname(path)), normalizePath(nested)),
        identical(output, "isolated"),
        identical(attr(output, "status", exact = TRUE), NULL)
    )
})
