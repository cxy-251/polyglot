# polyglot-covers: r.tooling.byte-compilation-and-namespace-native-registration

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root)
    namespace <- suppressMessages(loadNamespace(
        "polyglotrfixture",
        lib.loc = installed$library
    ))
    on.exit(unloadNamespace("polyglotrfixture"), add = TRUE)

    routines <- getDLLRegisteredRoutines("polyglotrfixture")
    compiled <- compiler::cmpfun(getExportedValue("polyglotrfixture", "double_value"))

    stopifnot(
        "C_polyglot_double" %in% names(routines$.Call),
        identical(compiled(c(2, 4)), c(4, 8)),
        isNamespace(namespace)
    )
})
