# polyglot-family: collections_and_iteration
# polyglot-concept: sets_membership_and_deduplication
# polyglot-related: languages/r/language/08_collection_workflows_and_tabular_data/
# polyglot-related+: test_063_set_operations_unique_inputs_and_types.R
#
# 共同问题：成员测试、去重和集合运算保留什么顺序与类型。
# 对照观察：base R 以去重向量表达集合；`unique` 保留首次出现顺序，集合函数忽略重复。

values <- c("b", "a", "b")

stopifnot(
    identical(unique(values), c("b", "a")),
    identical(values %in% c("a", "c"), c(FALSE, TRUE, FALSE)),
    setequal(union(c(1L, 1L), c(2L, 1L)), c(1L, 2L)),
    identical(intersect(c("b", "a"), c("a", "c")), "a")
)
