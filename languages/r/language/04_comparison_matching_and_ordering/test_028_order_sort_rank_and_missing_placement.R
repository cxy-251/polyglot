# polyglot-covers: r.language.order-sort-rank-and-missing-placement

values <- c(NA_real_, 2, 1, 2)

stopifnot(
    identical(order(values, na.last = TRUE), c(3L, 2L, 4L, 1L)),
    identical(sort(values, na.last = TRUE), c(1, 2, 2, NA_real_)),
    identical(sort(values, na.last = NA), c(1, 2, 2)),
    identical(rank(c(20, 10, 20), ties.method = "average"), c(2.5, 1, 2.5)),
    identical(rank(c(20, 10, 20), ties.method = "first"), c(2L, 1L, 3L))
)
