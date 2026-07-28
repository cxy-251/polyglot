# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/r/tooling_and_runtime/14_packages_namespaces_and_tools/
# polyglot-related+: test_106_namespace_library_require_and_colon_operators.R
#
# 共同问题：加载失败是否留下半初始化 cache，后续探测怎样表现。
# 对照观察：`requireNamespace(..., quietly=TRUE)` 对不存在 package 返回 FALSE，不加入 loaded namespace。

name <- "polyglot.package.that.does.not.exist"
before <- loadedNamespaces()
available <- requireNamespace(name, quietly = TRUE)
after <- loadedNamespaces()

stopifnot(
    identical(available, FALSE),
    !(name %in% after),
    identical(before, after)
)
