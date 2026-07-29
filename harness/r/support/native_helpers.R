polyglot_native_source <- function() {
    normalizePath(
        file.path("harness", "r", "native", "polyglot_native.c"),
        mustWork = TRUE
    )
}

build_polyglot_native <- function(root) {
    source <- file.path(root, "polyglot_native.c")
    stopifnot(file.copy(polyglot_native_source(), source))
    old_directory <- setwd(root)
    on.exit(setwd(old_directory), add = TRUE)
    output <- system2(
        file.path(R.home("bin"), "R"),
        c("CMD", "SHLIB", "polyglot_native.c", "-o", "polyglotnative.so"),
        stdout = TRUE,
        stderr = TRUE
    )
    status <- attr(output, "status", exact = TRUE)
    stopifnot(is.null(status) || identical(status, 0L))
    library <- normalizePath(file.path(root, "polyglotnative.so"), mustWork = TRUE)
    stopifnot(file.exists(library))
    library
}
