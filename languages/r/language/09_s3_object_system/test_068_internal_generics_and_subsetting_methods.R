# polyglot-covers: r.language.s3-internal-generics-and-replacement-methods

new_window <- function(values) structure(values, class = "window")
`[.window` <- function(x, i, ...) {
    result <- NextMethod("[")
    structure(result, class = "window")
}
length.window <- function(x) length(unclass(x)) * 10L
`[<-.window` <- function(x, i, value) {
    if (any(value < 0)) {
        stop(structure(
            list(message = "negative value", call = NULL, value = value),
            class = c("polyglot_window_error", "error", "condition")
        ))
    }
    structure(NextMethod("[<-"), class = "window")
}

value <- new_window(1:4)
slice <- value[2:3]
value[2L] <- 9L
invalid <- tryCatch({
    value[1L] <- -1L
}, error = identity)

stopifnot(
    inherits(slice, "window"),
    identical(unclass(slice), 2:3),
    identical(length(value), 40L),
    identical(length(unclass(value)), 4L),
    identical(unclass(value), c(1L, 9L, 3L, 4L)),
    inherits(invalid, "polyglot_window_error"),
    identical(invalid$value, -1L)
)

# `[`, `[<-` 与 length 都是 S3 dispatch 点；replacement method 返回的新值会由赋值语法重新绑定。
