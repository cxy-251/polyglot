# polyglot-covers: r.tooling.package-attachment-lifecycle-and-namespace-cache

local({
    package_library <- normalizePath(
        Sys.getenv("POLYGLOT_R_PACKAGE_LIBRARY"),
        mustWork = TRUE
    )
    old_paths <- .libPaths()
    on.exit(.libPaths(old_paths), add = TRUE)
    .libPaths(c(package_library, old_paths))

    first_namespace <- suppressMessages(loadNamespace("polyglotrfixture", lib.loc = package_library))
    second_namespace <- suppressMessages(loadNamespace("polyglotrfixture", lib.loc = package_library))

    startup <- capture.output(
        suppressPackageStartupMessages(library("polyglotrfixture", character.only = TRUE)),
        type = "message"
    )
    on.exit(detach("package:polyglotrfixture", unload = TRUE, character.only = TRUE), add = TRUE)

    stopifnot(
        "package:polyglotrfixture" %in% search(),
        identical(double_value(4), 8),
        identical(startup, character(0)),
        identical(first_namespace, second_namespace),
        identical(
            find.package("polyglotrfixture", lib.loc = package_library),
            file.path(package_library, "polyglotrfixture")
        )
    )
})

# namespace 先缓存再 attach 到 search path；detach 与 unload 是两个生命周期动作。
