# polyglot-covers: r.tooling.namespace-library-require-and-colon-operators

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root)

    namespace <- suppressMessages(loadNamespace(
        "polyglotrfixture",
        lib.loc = installed$library
    ))
    on.exit(unloadNamespace("polyglotrfixture"), add = TRUE)

    stopifnot(
        identical(as.character(getNamespaceName(namespace)), "polyglotrfixture"),
        identical(getExportedValue("polyglotrfixture", "double_value")(2), 4),
        identical(getFromNamespace("internal_identity", "polyglotrfixture")("x"), "x"),
        requireNamespace("polyglotrfixture", quietly = TRUE, lib.loc = installed$library)
    )
})
