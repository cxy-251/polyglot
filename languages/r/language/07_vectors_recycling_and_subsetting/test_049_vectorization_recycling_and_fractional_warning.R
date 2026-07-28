# polyglot-covers: r.language.vectorization-recycling-and-fractional-warning

stopifnot(
    identical(1:4 + 10L, 11:14),
    identical(1:4 + c(10L, 20L), c(11L, 22L, 13L, 24L))
)

warning_condition <- NULL
result <- withCallingHandlers(
    1:5 + c(10L, 20L),
    warning = function(condition) {
        warning_condition <<- condition
        invokeRestart("muffleWarning")
    }
)
stopifnot(
    identical(result, c(11L, 22L, 13L, 24L, 15L)),
    inherits(warning_condition, "warning")
)
