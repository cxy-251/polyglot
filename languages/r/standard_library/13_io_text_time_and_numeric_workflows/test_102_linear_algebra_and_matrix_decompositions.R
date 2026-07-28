# polyglot-covers: r.standard-library.linear-algebra-and-matrix-decompositions

matrix <- matrix(c(4, 1, 1, 3), nrow = 2)
right_hand_side <- c(1, 2)
solution <- solve(matrix, right_hand_side)
decomposition <- eigen(matrix, symmetric = TRUE)

stopifnot(
    isTRUE(all.equal(matrix %*% solution, matrix(right_hand_side, ncol = 1))),
    identical(crossprod(1:3), matrix(14, nrow = 1)),
    all(decomposition$values > 0),
    isTRUE(all.equal(qr.Q(qr(matrix)) %*% qr.R(qr(matrix)), matrix))
)
