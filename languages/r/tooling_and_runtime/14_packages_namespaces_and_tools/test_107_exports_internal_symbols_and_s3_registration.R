# polyglot-covers: r.tooling.exports-internal-symbols-and-s3-registration

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root)
    old_paths <- .libPaths()
    on.exit(.libPaths(old_paths), add = TRUE)
    .libPaths(c(installed$library, old_paths))

    suppressMessages(loadNamespace("polyglotrfixture"))
    on.exit(unloadNamespace("polyglotrfixture"), add = TRUE)
    exports <- getNamespaceExports("polyglotrfixture")
    method <- getS3method("print", "polyglot_label")

    stopifnot(
        setequal(exports, c("double_value", "new_polyglot_label", ".Last.lib")),
        is.function(method),
        !("internal_identity" %in% exports),
        identical(polyglotrfixture::double_value(3), 6)
    )
})
