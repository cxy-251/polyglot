# polyglot-family: collections_and_iteration
# polyglot-concept: mapping_lookup_and_missing_keys
# polyglot-related: languages/r/language/06_scope_environments_and_call_frames/
# polyglot-related+: test_044_get_assign_exists_and_inherits_flags.R
#
# 共同问题：键查找成功、缺失与默认值怎样区分。
# 对照观察：named list 的 `$` 缺失返回 NULL，`[[` 可失败；environment 提供精确存在性检测。

mapping <- list(answer = 42L)
environment <- list2env(mapping, parent = emptyenv())

stopifnot(
    identical(mapping[["answer"]], 42L),
    is.null(mapping$missing),
    is.null(mapping[["missing"]]),
    exists("answer", environment, inherits = FALSE),
    !exists("missing", environment, inherits = FALSE)
)
