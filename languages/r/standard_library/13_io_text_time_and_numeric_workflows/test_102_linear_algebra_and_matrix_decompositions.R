# polyglot-covers: r.standard-library.statistics-linear-algebra-and-decompositions

matrix <- matrix(c(4, 1, 1, 3), nrow = 2)
right_hand_side <- c(1, 2)
solution <- solve(matrix, right_hand_side)
decomposition <- eigen(matrix, symmetric = TRUE)

stopifnot(
    identical(mean(c(1, 2, 3)), 2),
    isTRUE(all.equal(stats::var(c(1, 2, 3)), 1)),
    isTRUE(all.equal(matrix %*% solution, matrix(right_hand_side, ncol = 1))),
    identical(crossprod(1:3), matrix(14, nrow = 1)),
    all(decomposition$values > 0),
    isTRUE(all.equal(qr.Q(qr(matrix)) %*% qr.R(qr(matrix)), matrix))
)

# 统计摘要返回普通向量；线性代数入口保持矩阵形状，并应以重构不变量而非精确算法细节验证。
