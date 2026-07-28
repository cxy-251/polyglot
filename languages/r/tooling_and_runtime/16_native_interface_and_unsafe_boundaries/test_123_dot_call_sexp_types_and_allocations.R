# polyglot-covers: r.tooling.dot-call-sexp-types-and-allocations

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    result <- .Call("C_polyglot_double", c(1, 2, 3), PACKAGE = "polyglotnative")
    type_error <- tryCatch(
        .Call("C_polyglot_double", 1:3, PACKAGE = "polyglotnative"),
        error = identity
    )

    stopifnot(
        identical(result, c(2, 4, 6)),
        identical(typeof(result), "double"),
        inherits(type_error, "error")
    )
})
