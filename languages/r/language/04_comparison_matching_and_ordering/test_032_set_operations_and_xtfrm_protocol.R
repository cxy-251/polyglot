# polyglot-covers: r.language.set-operations-and-xtfrm-protocol

left <- c(1L, 2L, 2L)
right <- c(2L, 3L)
factor_value <- factor(c("b", "a"), levels = c("a", "b"))

stopifnot(
    identical(union(left, right), 1:3),
    identical(intersect(left, right), 2L),
    identical(setdiff(left, right), 1L),
    setequal(c(1L, 1L, 2L), c(2L, 1L)),
    identical(xtfrm(factor_value), c(2L, 1L)),
    identical(order(factor_value), c(2L, 1L))
)
