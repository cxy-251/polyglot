# polyglot-covers: r.tooling.native-symbol-registration-and-lookup

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)
    routines <- getDLLRegisteredRoutines(dll)

    stopifnot(
        "polyglot_scale" %in% names(routines$.C),
        "C_polyglot_double" %in% names(routines$.Call),
        identical(routines$.C$polyglot_scale$numParameters, 3L),
        identical(routines$.Call$C_polyglot_double$numParameters, 1L)
    )
})
