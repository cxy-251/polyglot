# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/r/tooling_and_runtime/14_packages_namespaces_and_tools/
# polyglot-related+: test_112_byte_compilation_and_namespace_native_registration.R
#
# 共同问题：初始化是否缓存，动态库怎样关联 namespace。
# 对照观察：同名 namespace 在进程内缓存为同一 environment；注册 native routine 挂在已加载 DLL 表。

first <- loadNamespace("splines")
second <- loadNamespace("splines")
routines <- getDLLRegisteredRoutines("splines")

stopifnot(
    identical(first, second),
    isNamespace(first),
    "splines" %in% names(getLoadedDLLs()),
    is.list(routines)
)
