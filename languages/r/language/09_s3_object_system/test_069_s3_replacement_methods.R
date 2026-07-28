# polyglot-covers: r.language.s3-replacement-methods

new_nonnegative <- function(values) structure(values, class = "nonnegative")
`[<-.nonnegative` <- function(x, i, value) {
    if (any(value < 0)) {
        stop("values must be nonnegative")
    }
    result <- NextMethod("[<-")
    structure(result, class = "nonnegative")
}

value <- new_nonnegative(c(1, 2, 3))
value[2] <- 9
error <- tryCatch({
    value[1] <- -1
    NULL
}, error = identity)

stopifnot(
    identical(unclass(value), c(1, 9, 3)),
    inherits(value, "nonnegative"),
    inherits(error, "error"),
    grepl("nonnegative", conditionMessage(error), fixed = TRUE)
)
