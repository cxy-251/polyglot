# polyglot-covers: r.language.equality-missing-values-and-floating-tolerance

left <- c(a = 1, b = 2)
right <- c(a = 1, b = 2)
different_attributes <- unname(right)

stopifnot(
    all(left == right),
    identical(left, right),
    !identical(left, different_attributes),
    isTRUE(all.equal(left, different_attributes, check.attributes = FALSE)),
    is.character(all.equal(left, different_attributes)),
    is.na(NA == NA),
    is.na(NaN == NaN),
    identical(NA, NA),
    identical(NaN, NaN),
    !is.nan(NA_real_),
    is.nan(NaN),
    identical(is.na(c(1, NA, NaN)), c(FALSE, TRUE, TRUE))
)

sum_value <- 0.1 + 0.2
stopifnot(
    !identical(sum_value, 0.3),
    sum_value != 0.3,
    isTRUE(all.equal(sum_value, 0.3)),
    abs(sum_value - 0.3) < .Machine$double.eps
)

# `==` 向量化并传播未知值；identical 检查类型与属性；all.equal 表达带容差的近似比较。
