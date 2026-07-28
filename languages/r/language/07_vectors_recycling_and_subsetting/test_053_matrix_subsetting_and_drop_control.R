# polyglot-covers: r.language.matrix-subsetting-and-drop-control

value <- matrix(1:6, nrow = 2L, dimnames = list(c("r1", "r2"), c("a", "b", "c")))

row_vector <- value[1L, ]
row_matrix <- value[1L, , drop = FALSE]

stopifnot(
    identical(row_vector, c(a = 1L, b = 3L, c = 5L)),
    identical(dim(row_matrix), c(1L, 3L)),
    identical(value[cbind(c(1L, 2L), c(1L, 3L))], c(1L, 6L)),
    identical(value[, "b"], c(r1 = 3L, r2 = 4L)),
    identical(value[, "b", drop = FALSE], value[, 2L, drop = FALSE])
)
