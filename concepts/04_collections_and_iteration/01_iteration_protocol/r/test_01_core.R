# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/r/language/08_collection_workflows_and_tabular_data/
# polyglot-related+: test_059_apply_lapply_sapply_and_vapply_contracts.R
#
# 共同问题：集合怎样产生元素，循环何时终止。
# 对照观察：base R 没有用户可实现的统一 iterator protocol；`for` 直接遍历向量或 list。

values <- list(1L, 2L, 3L)
seen <- integer()
for (value in values) {
    seen <- c(seen, value)
}

stopifnot(
    identical(seen, 1:3),
    identical(seq_along(values), 1:3),
    identical(unlist(lapply(values, identity)), 1:3)
)
