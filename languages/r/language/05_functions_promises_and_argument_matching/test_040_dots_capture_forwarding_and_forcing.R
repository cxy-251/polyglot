# polyglot-covers: r.language.dots-capture-forwarding-and-forcing

counter <- 0L
ignore_dots <- function(...) ...length()
capture_dots <- function(...) list(length = ...length(), names = ...names(), values = list(...))

stopifnot(identical(ignore_dots({ counter <- counter + 1L }), 1L), counter == 0L)

captured <- capture_dots(first = { counter <- counter + 1L; 1L }, second = 2L)
stopifnot(
    identical(captured$length, 2L),
    identical(captured$names, c("first", "second")),
    identical(captured$values, list(first = 1L, second = 2L)),
    counter == 1L
)
