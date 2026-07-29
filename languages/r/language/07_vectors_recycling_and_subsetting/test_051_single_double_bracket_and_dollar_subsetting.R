# polyglot-covers: r.language.subsetting-index-kinds-and-drop

value <- list(first = 1L, second = list(answer = 42L))

stopifnot(
    identical(value["first"], list(first = 1L)),
    identical(value[["first"]], 1L),
    identical(value$first, 1L),
    identical(value[[c("second", "answer")]], 42L),
    is.null(value$missing),
    is.null(value[["missing"]]),
    inherits(tryCatch(value[[3L]], error = identity), "error")
)

named <- c(a = 10L, b = 20L, c = 30L, d = 40L)
stopifnot(
    identical(named[-c(1L, 4L)], c(b = 20L, c = 30L)),
    identical(named[c(TRUE, FALSE)], c(a = 10L, c = 30L)),
    identical(named[c("d", "a")], c(d = 40L, a = 10L)),
    inherits(tryCatch(named[c(-1L, 2L)], error = identity), "error")
)

matrix_value <- matrix(1:6, nrow = 2L, dimnames = list(c("r1", "r2"), c("a", "b", "c")))
row_vector <- matrix_value[1L, ]
row_matrix <- matrix_value[1L, , drop = FALSE]
stopifnot(
    identical(row_vector, c(a = 1L, b = 3L, c = 5L)),
    identical(dim(row_matrix), c(1L, 3L)),
    identical(matrix_value[cbind(c(1L, 2L), c(1L, 3L))], c(1L, 6L))
)

# `[` 保持容器形状，`[[` 取单元素，`$` 是 name 语法；矩阵默认 drop 可用显式 FALSE 禁止。
