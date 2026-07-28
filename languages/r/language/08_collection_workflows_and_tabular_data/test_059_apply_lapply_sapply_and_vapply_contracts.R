# polyglot-covers: r.language.apply-lapply-sapply-and-vapply-contracts

values <- list(first = 1:2, second = 3:5)

stopifnot(
    identical(lapply(values, sum), list(first = 3L, second = 12L)),
    identical(sapply(values, length), c(first = 2L, second = 3L)),
    identical(vapply(values, length, integer(1)), c(first = 2L, second = 3L)),
    inherits(tryCatch(vapply(values, identity, integer(1)), error = identity), "error"),
    identical(apply(matrix(1:4, nrow = 2L), 2L, sum), c(3L, 7L))
)
