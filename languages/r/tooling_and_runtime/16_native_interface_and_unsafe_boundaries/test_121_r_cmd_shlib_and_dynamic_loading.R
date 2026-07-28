# polyglot-covers: r.tooling.r-cmd-shlib-and-dynamic-loading

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    library <- build_polyglot_native(root)
    dll <- dyn.load(library, local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    stopifnot(
        identical(dll[["name"]], "polyglotnative"),
        is.loaded("C_polyglot_double", PACKAGE = "polyglotnative"),
        file.exists(dll[["path"]])
    )
})
