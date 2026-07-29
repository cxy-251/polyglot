# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/r/language/04_comparison_matching_and_ordering/
# polyglot-related+: test_028_order_sort_rank_and_missing_placement.R
#
# 共同问题：排序是否稳定，如何指定 key、降序和缺失位置。
# 对照观察：`order(method="radix")` 稳定返回索引，可组合多列 key 并显式放置 NA。

rows <- data.frame(key = c(2L, 1L, 2L), label = c("a", "b", "c"))
indices <- order(rows$key, method = "radix")

stopifnot(
    identical(indices, c(2L, 1L, 3L)),
    identical(rows$label[indices], c("b", "a", "c")),
    identical(sort(c(2L, NA_integer_, 1L), na.last = FALSE), c(NA_integer_, 1L, 2L))
)
