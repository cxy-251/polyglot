# polyglot-covers: r.language.s3-class-vectors-generics-and-usemethod

describe <- function(x, ...) UseMethod("describe")
describe.default <- function(x, ...) paste("default", typeof(x))
describe.measurement <- function(x, ...) paste(attr(x, "unit"), unclass(x))

value <- structure(12, class = c("measurement", "numeric"), unit = "kg")

stopifnot(
    identical(class(value), c("measurement", "numeric")),
    identical(describe(value), "kg 12"),
    identical(describe(TRUE), "default logical"),
    !exists(".Generic", inherits = FALSE)
)
