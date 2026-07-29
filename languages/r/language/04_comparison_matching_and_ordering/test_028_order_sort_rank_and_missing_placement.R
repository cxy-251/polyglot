# polyglot-covers: r.language.order-rank-match-and-deduplication

values <- c(NA_real_, 2, 1, 2)
table <- c("red", "green", NA_character_)
duplicates <- c(1, 1, NA_real_, NA_real_, NaN, NaN, -0, 0)

stopifnot(
    identical(order(values, na.last = TRUE), c(3L, 2L, 4L, 1L)),
    identical(sort(values, na.last = TRUE), c(1, 2, 2, NA_real_)),
    identical(sort(values, na.last = NA), c(1, 2, 2)),
    identical(rank(c(20, 10, 20), ties.method = "average"), c(2.5, 1, 2.5)),
    identical(rank(c(20, 10, 20), ties.method = "first"), c(2L, 1L, 3L)),
    identical(match(c("green", "blue"), table), c(2L, NA_integer_)),
    identical(match(c("green", "blue"), table, nomatch = 0L), c(2L, 0L)),
    identical(c("red", "blue") %in% table, c(TRUE, FALSE)),
    identical(match(NA_character_, table), 3L),
    identical(match(c(NA_real_, NaN), c(NaN, NA_real_)), c(2L, 1L)),
    identical(duplicated(duplicates), c(FALSE, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, TRUE)),
    identical(unique(duplicates), c(1, NA_real_, NaN, 0)),
    identical(anyDuplicated(duplicates), 2L)
)

# order 返回置换、sort 返回值、rank 处理 ties；match/duplicated 对 NA 与 NaN 有明确键语义。
