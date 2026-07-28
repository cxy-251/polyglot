# polyglot-covers: r.language.class-vectors-inherits-and-unclass

object <- structure(1:3, class = c("polyglot_count", "integer"), unit = "items")
plain <- unclass(object)

stopifnot(
    identical(class(object), c("polyglot_count", "integer")),
    inherits(object, "polyglot_count"),
    inherits(object, "integer"),
    identical(typeof(plain), "integer"),
    is.null(attr(plain, "class")),
    identical(attr(plain, "unit"), "items")
)
