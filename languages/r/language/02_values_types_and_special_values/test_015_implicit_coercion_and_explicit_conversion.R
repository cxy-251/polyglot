# polyglot-covers: r.language.coercion-attributes-and-class-vectors

mixed_numeric <- c(TRUE, 2L, 3.5)
mixed_text <- c(TRUE, 2L, "three")
preserved <- list(TRUE, 2L, "three")
value <- 1:4
names(value) <- letters[1:4]
attr(value, "source") <- "course"
dim(value) <- c(2L, 2L)
class(value) <- c("polyglot_matrix", "matrix", "array")

stopifnot(
    identical(mixed_numeric, c(1, 2, 3.5)),
    identical(typeof(mixed_numeric), "double"),
    identical(mixed_text, c("TRUE", "2", "three")),
    identical(vapply(preserved, typeof, ""), c("logical", "integer", "character")),
    identical(as.integer("12"), 12L),
    is.na(suppressWarnings(as.integer("bad"))),
    identical(dim(value), c(2L, 2L)),
    identical(attr(value, "source"), "course"),
    identical(class(value), c("polyglot_matrix", "matrix", "array")),
    inherits(value, "matrix"),
    is.null(names(value))
)

# 原子向量合并时采用共同类型；list 保留元素类型。特殊属性 accessor 还会维护对象不变量。
named <- structure(1:3, names = c("a", "b", "c"), source = "input")
subset <- named[1:2]
plain <- as.vector(named)
stopifnot(
    identical(names(subset), c("a", "b")),
    is.null(attr(subset, "source")),
    identical(names(named + 1L), names(named)),
    is.null(attributes(plain)),
    identical(plain, 1:3)
)
