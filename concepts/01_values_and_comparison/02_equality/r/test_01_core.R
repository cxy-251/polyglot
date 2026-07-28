# polyglot-family: values_and_comparison
# polyglot-concept: equality
# polyglot-related: languages/r/language/04_comparison_matching_and_ordering/
# polyglot-related+: test_025_value_identity_and_approximate_equality.R
#
# 共同问题：值相等、严格相同和近似相等分别如何表达。
# 对照观察：`==` 向量化并传播 NA；`identical` 严格比较类型，`all.equal` 表达容差。

stopifnot(
    identical(c(1, 2) == c(1, 3), c(TRUE, FALSE)),
    is.na(NA_real_ == NA_real_),
    !identical(1L, 1),
    isTRUE(all.equal(0.1 + 0.2, 0.3))
)
