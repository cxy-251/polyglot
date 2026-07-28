# polyglot-covers: r.language.single-double-bracket-and-dollar-subsetting

value <- list(first = 1L, second = list(answer = 42L))

stopifnot(
    identical(value["first"], list(first = 1L)),
    identical(value[["first"]], 1L),
    identical(value$first, 1L),
    identical(value[[c("second", "answer")]], 42L),
    is.null(value$missing),
    is.null(value[["missing"]]),
    inherits(tryCatch(value[[3L]], error = identity), "error")
)
