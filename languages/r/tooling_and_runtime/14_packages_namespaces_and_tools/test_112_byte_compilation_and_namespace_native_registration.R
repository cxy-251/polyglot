# polyglot-covers: r.tooling.byte-compilation-and-package-native-registration

local({
    package_library <- normalizePath(
        Sys.getenv("POLYGLOT_R_PACKAGE_LIBRARY"),
        mustWork = TRUE
    )
    namespace <- suppressMessages(loadNamespace(
        "polyglotrfixture",
        lib.loc = package_library
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

# cmpfun 保持函数接口；NAMESPACE 的 useDynLib 注册表把 R wrapper 绑定到已加载 native symbol。
