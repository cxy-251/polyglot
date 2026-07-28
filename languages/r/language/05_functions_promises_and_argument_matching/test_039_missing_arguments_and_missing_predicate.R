# polyglot-covers: r.language.missing-arguments-and-missing-predicate

inspect_missing <- function(required, optional = 2L) {
    c(required = missing(required), optional = missing(optional))
}

stopifnot(
    identical(inspect_missing(), c(required = TRUE, optional = TRUE)),
    identical(inspect_missing(1L), c(required = FALSE, optional = TRUE)),
    identical(inspect_missing(1L, 3L), c(required = FALSE, optional = FALSE)),
    inherits(tryCatch((function(value) value)(), error = identity), "error")
)
