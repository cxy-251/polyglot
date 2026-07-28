# polyglot-covers: r.language.matrix-array-and-column-major-order

matrix_value <- matrix(1:6, nrow = 2L, dimnames = list(c("r1", "r2"), c("a", "b", "c")))
array_value <- array(1:8, dim = c(2L, 2L, 2L))

stopifnot(
    identical(dim(matrix_value), c(2L, 3L)),
    identical(matrix_value[2L, 3L], 6L),
    identical(as.vector(matrix_value), 1:6),
    identical(matrix_value["r1", ], c(a = 1L, b = 3L, c = 5L)),
    identical(dim(array_value), c(2L, 2L, 2L)),
    identical(array_value[2L, 1L, 2L], 6L)
)
