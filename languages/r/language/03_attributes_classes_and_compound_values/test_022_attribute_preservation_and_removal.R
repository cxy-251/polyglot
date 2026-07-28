# polyglot-covers: r.language.attribute-preservation-and-removal

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
