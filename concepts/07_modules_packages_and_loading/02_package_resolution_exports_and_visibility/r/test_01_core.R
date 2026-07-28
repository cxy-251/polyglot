# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/r/tooling_and_runtime/14_packages_namespaces_and_tools/
# polyglot-related+: test_107_exports_internal_symbols_and_s3_registration.R
#
# 共同问题：package 怎样解析，公开与内部名称怎样区分。
# 对照观察：`::` 只访问 NAMESPACE export；`:::` 可越过可见性边界，应仅用于准确说明内部机制。

exports <- getNamespaceExports("stats")
internal <- getFromNamespace(".approxfun", "stats")

stopifnot(
    "lm" %in% exports,
    inherits(stats::lm(mpg ~ wt, data = datasets::mtcars), "lm"),
    is.function(internal),
    !(".approxfun" %in% exports)
)
