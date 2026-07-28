# polyglot-covers: r.language.s3-internal-generics-and-subsetting-methods

new_window <- function(values) structure(values, class = "window")
`[.window` <- function(x, i, ...) {
    result <- NextMethod("[")
    structure(result, class = "window")
}
length.window <- function(x) length(unclass(x)) * 10L

value <- new_window(1:4)
slice <- value[2:3]

stopifnot(
    inherits(slice, "window"),
    identical(unclass(slice), 2:3),
    identical(length(value), 40L),
    identical(length(unclass(value)), 4L)
)
