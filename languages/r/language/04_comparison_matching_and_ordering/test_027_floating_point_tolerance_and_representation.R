# polyglot-covers: r.language.floating-point-tolerance-and-representation

sum_value <- 0.1 + 0.2

stopifnot(
    !identical(sum_value, 0.3),
    sum_value != 0.3,
    isTRUE(all.equal(sum_value, 0.3)),
    abs(sum_value - 0.3) < .Machine$double.eps,
    identical(sprintf("%.17g", sum_value), "0.30000000000000004")
)
