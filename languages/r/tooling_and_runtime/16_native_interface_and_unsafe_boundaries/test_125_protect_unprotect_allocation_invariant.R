# polyglot-covers: r.tooling.protect-unprotect-allocation-invariant

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    results <- lapply(seq_len(100L), function(index) {
        .Call("C_polyglot_double", as.double(index), PACKAGE = "polyglotnative")
    })
    invisible(gc())

    stopifnot(
        identical(unlist(results), as.double(seq_len(100L) * 2L)),
        identical(results[[100L]], 200)
    )
})
