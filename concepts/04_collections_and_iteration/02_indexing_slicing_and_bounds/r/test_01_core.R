# polyglot-family: collections_and_iteration
# polyglot-concept: indexing_slicing_and_bounds
# polyglot-related: languages/r/language/07_vectors_recycling_and_subsetting/
# polyglot-related+: test_051_single_double_bracket_and_dollar_subsetting.R
#
# 共同问题：索引基数、切片结果和越界行为是什么。
# 对照观察：R 使用 1-based 索引；`[` 保持容器，`[[` 提取单值，越界 `[` 产生 NA。

value <- c(a = 10L, b = 20L)

stopifnot(
    identical(value[1L], c(a = 10L)),
    identical(value[[1L]], 10L),
    is.na(value[3L]),
    inherits(tryCatch(value[[3L]], error = identity), "error"),
    identical(value[2:1], c(b = 20L, a = 10L))
)
