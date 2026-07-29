# polyglot-covers: r.language.s3-usemethod-lookup-and-lazy-arguments

describe <- function(x, ...) UseMethod("describe")
describe.default <- function(x, ...) paste("default", typeof(x))
describe.measurement <- function(x, ...) paste(attr(x, "unit"), unclass(x))

value <- structure(12, class = c("measurement", "numeric"), unit = "kg")
both <- structure(1L, class = c("unknown", "measurement", "numeric"), unit = "m")

counter <- 0L
lazy_describe <- function(x, unused) UseMethod("lazy_describe")
lazy_describe.default <- function(x, unused) x$value
lazy_value <- structure(list(value = 7L), class = "polyglot_value")
lazy_result <- lazy_describe(lazy_value, {
    counter <- counter + 1L
    stop("must remain lazy")
})

stopifnot(
    identical(class(value), c("measurement", "numeric")),
    identical(describe(value), "kg 12"),
    identical(describe(TRUE), "default logical"),
    identical(describe(both), "m 1"),
    identical(getS3method("describe", "measurement"), describe.measurement),
    is.null(getS3method("describe", "missing", optional = TRUE)),
    identical(lazy_result, 7L),
    counter == 0L,
    !exists(".Generic", inherits = FALSE)
)

# UseMethod 沿 class vector 查找首个方法，再退到 default；未使用的 promise 不因分派而强制。
