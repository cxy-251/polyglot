# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/r/language/07_vectors_recycling_and_subsetting/
# polyglot-related+: test_053_matrix_subsetting_and_drop_control.R
#
# 共同问题：切片是 view 还是副本；结构修改后旧切片如何变化。
# 对照观察：base R 的普通 `[` 不提供可写 view；子集是独立值，matrix 的 `drop` 另行控制形状。

matrix_value <- matrix(1:6, nrow = 2)
column <- matrix_value[, 1L, drop = FALSE]
matrix_value[1L, 1L] <- 99L

stopifnot(
    identical(column, matrix(1:2, nrow = 2)),
    identical(matrix_value[1L, 1L], 99L),
    identical(dim(column), c(2L, 1L)),
    is.null(dim(matrix_value[, 1L]))
)
