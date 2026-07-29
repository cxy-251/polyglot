# polyglot-covers: r.language.missing-arguments-and-lazy-dots

inspect_missing <- function(required, optional = 2L) {
    c(required = missing(required), optional = missing(optional))
}

stopifnot(
    identical(inspect_missing(), c(required = TRUE, optional = TRUE)),
    identical(inspect_missing(1L), c(required = FALSE, optional = TRUE)),
    identical(inspect_missing(1L, 3L), c(required = FALSE, optional = FALSE)),
    inherits(tryCatch((function(value) value)(), error = identity), "error")
)

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

# missing() 观察调用是否提供参数；...length/...names 不强制 promise，而 list(...) 会强制。
