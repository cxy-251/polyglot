# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/r/language/06_scope_environments_and_call_frames/
# polyglot-related+: test_042_environment_reference_semantics_and_locking.R
#
# 共同问题：导出可变值后，使用者拿到别名还是快照。
# 对照观察：environment export 保留引用身份；普通向量读取后呈现 copy-on-modify 值语义。

module <- new.env(parent = emptyenv())
module$state <- new.env(parent = emptyenv())
module$state$count <- 0L
module$values <- 1:2
state_alias <- module$state
value_copy <- module$values
state_alias$count <- 1L
module$values[1L] <- 9L

stopifnot(
    identical(module$state$count, 1L),
    identical(value_copy, 1:2)
)
