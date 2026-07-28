# polyglot-covers: r.tooling.dot-c-copying-and-ownership-boundary

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    original <- c(1, 2, NA_real_)
    rejected <- tryCatch(
        .C(
            "polyglot_scale",
            values = original,
            length = as.integer(length(original)),
            factor = 3,
            PACKAGE = "polyglotnative"
        ),
        error = identity
    )
    result <- .C(
        "polyglot_scale",
        values = original,
        length = as.integer(length(original)),
        factor = 3,
        NAOK = TRUE,
        PACKAGE = "polyglotnative"
    )

    stopifnot(
        inherits(rejected, "error"),
        identical(result$values, c(3, 6, NA_real_)),
        identical(original, c(1, 2, NA_real_)),
        identical(result$length, 3L)
    )
})
