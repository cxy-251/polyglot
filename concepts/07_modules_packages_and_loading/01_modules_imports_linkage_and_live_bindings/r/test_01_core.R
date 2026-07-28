# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/r/tooling_and_runtime/14_packages_namespaces_and_tools/
# polyglot-related+: test_105_source_local_and_chdir_environments.R
#
# 共同问题：代码单元怎样加载到独立作用域，导入绑定是否实时。
# 对照观察：`source(local=environment)` 显式选择目标环境；environment 访问保持 live binding。

local({
    path <- tempfile("polyglot-r-module-", fileext = ".R")
    on.exit(unlink(path, force = TRUE), add = TRUE)
    writeLines("value <- 1L", path)
    module <- new.env(parent = baseenv())
    source(path, local = module)
    alias <- module
    module$value <- 2L

    stopifnot(identical(alias$value, 2L), !exists("value", inherits = FALSE))
})
