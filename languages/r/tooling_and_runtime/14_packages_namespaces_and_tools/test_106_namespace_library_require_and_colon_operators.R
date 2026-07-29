# polyglot-covers: r.tooling.package-namespaces-exports-and-s3-registration

local({
    package_library <- normalizePath(
        Sys.getenv("POLYGLOT_R_PACKAGE_LIBRARY"),
        mustWork = TRUE
    )
    old_paths <- .libPaths()
    on.exit(.libPaths(old_paths), add = TRUE)
    .libPaths(c(package_library, old_paths))

    namespace <- suppressMessages(loadNamespace(
        "polyglotrfixture",
        lib.loc = package_library
    ))
    on.exit(unloadNamespace("polyglotrfixture"), add = TRUE)
    exports <- getNamespaceExports("polyglotrfixture")
    method <- getS3method("print", "polyglot_label")

    stopifnot(
        identical(as.character(getNamespaceName(namespace)), "polyglotrfixture"),
        identical(getExportedValue("polyglotrfixture", "double_value")(2), 4),
        identical(getFromNamespace("internal_identity", "polyglotrfixture")("x"), "x"),
        requireNamespace("polyglotrfixture", quietly = TRUE, lib.loc = package_library),
        setequal(exports, c("double_value", "new_polyglot_label", ".Last.lib")),
        is.function(method),
        !("internal_identity" %in% exports),
        identical(polyglotrfixture::double_value(3), 6)
    )
})

# loadNamespace 不 attach；`::` 只访问 export；`:::`/getFromNamespace 可越过封装，应限于诊断。
