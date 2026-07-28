# polyglot-covers: r.tooling.xlength-and-long-vector-interface-boundary

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    length_value <- .Call("C_polyglot_length", seq_len(1000L), PACKAGE = "polyglotnative")

    stopifnot(
        identical(length_value, 1000),
        identical(typeof(length_value), "double"),
        identical(length(seq_len(1000L)), 1000L)
    )
})
