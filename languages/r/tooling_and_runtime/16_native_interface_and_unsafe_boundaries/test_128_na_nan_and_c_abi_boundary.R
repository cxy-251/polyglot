# polyglot-covers: r.tooling.na-nan-and-c-abi-boundary

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    classify <- function(value) {
        .Call("C_polyglot_missing_kind", value, PACKAGE = "polyglotnative")
    }

    stopifnot(
        identical(classify(1), 0L),
        identical(classify(NA_real_), 1L),
        identical(classify(NaN), 2L),
        is.na(NA_real_),
        is.nan(NaN)
    )
})
