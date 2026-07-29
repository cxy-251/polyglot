# polyglot-covers: r.language.factor-matrix-data-frame-and-class-storage

value <- factor(c("high", "low", "high", NA), levels = c("low", "high"))
matrix_value <- matrix(1:6, nrow = 2L, dimnames = list(c("r1", "r2"), c("a", "b", "c")))
frame <- data.frame(
    id = 1:2,
    label = c("one", "two"),
    payload = I(list(list(value = 1L), list(value = 2L)))
)
object <- structure(1:3, class = c("polyglot_count", "integer"), unit = "items")
plain <- unclass(object)

stopifnot(
    identical(typeof(value), "integer"),
    identical(class(value), "factor"),
    identical(levels(value), c("low", "high")),
    identical(unclass(value), structure(c(2L, 1L, 2L, NA_integer_), levels = c("low", "high"))),
    identical(as.character(value), c("high", "low", "high", NA_character_)),
    identical(dim(matrix_value), c(2L, 3L)),
    identical(matrix_value[2L, 3L], 6L),
    identical(as.vector(matrix_value), 1:6),
    identical(matrix_value["r1", ], c(a = 1L, b = 3L, c = 5L)),
    inherits(frame, "data.frame"),
    identical(typeof(frame), "list"),
    identical(dim(frame), c(2L, 3L)),
    inherits(frame$payload, "AsIs"),
    identical(frame$payload[[2L]]$value, 2L),
    identical(class(object), c("polyglot_count", "integer")),
    inherits(object, "integer"),
    identical(typeof(plain), "integer"),
    is.null(attr(plain, "class")),
    identical(attr(plain, "unit"), "items")
)

# factor、matrix 和 data.frame 都建立在普通存储加属性之上，但各自 accessor 承担不同不变量。
