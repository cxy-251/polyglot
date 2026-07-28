# polyglot-covers: r.language.attributes-names-class-and-dimensions

value <- 1:4
names(value) <- letters[1:4]
attr(value, "source") <- "course"
dim(value) <- c(2L, 2L)
class(value) <- c("polyglot_matrix", "matrix", "array")

stopifnot(
    identical(dim(value), c(2L, 2L)),
    identical(attr(value, "source"), "course"),
    identical(class(value), c("polyglot_matrix", "matrix", "array")),
    inherits(value, "matrix"),
    is.null(names(value))
)
