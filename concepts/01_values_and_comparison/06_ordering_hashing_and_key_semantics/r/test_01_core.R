# polyglot-family: values_and_comparison
# polyglot-concept: ordering_hashing_and_key_semantics
# polyglot-related: languages/r/language/04_comparison_matching_and_ordering/
# polyglot-related+: test_031_hashed_environment_lookup_and_identity.R
#
# 共同问题：排序、去重和键查找采用什么相等规则。
# 对照观察：`match`/`duplicated` 处理 NA 与 NaN 的规则不同于 `==`；environment 可启用哈希表。

table <- c(NA_real_, NaN, 1, 1)
hashed <- new.env(hash = TRUE, parent = emptyenv())
hashed[["key"]] <- 42L

stopifnot(
    identical(match(c(NA_real_, NaN), table), c(1L, 2L)),
    identical(duplicated(table), c(FALSE, FALSE, FALSE, TRUE)),
    identical(sort(c(3L, 1L, 2L)), 1:3),
    identical(hashed[["key"]], 42L)
)
