# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/r/tooling_and_runtime/14_packages_namespaces_and_tools/
# polyglot-related+: test_109_library_trees_lazy_loading_and_package_cache.R
#
# 共同问题：能否定位 package 而不执行初始化代码。
# 对照观察：`find.package`/`installed.packages` 检查 library tree；`loadNamespace` 才执行 namespace 初始化。

before <- loadedNamespaces()
path <- find.package("MASS")
record <- installed.packages(lib.loc = dirname(path))["MASS", ]
after <- loadedNamespaces()

stopifnot(
    dir.exists(path),
    identical(unname(record[["Package"]]), "MASS"),
    !("MASS" %in% before),
    !("MASS" %in% after)
)
