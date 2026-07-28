# polyglot-covers: r.language.factor-codes-levels-and-missing-values

value <- factor(c("high", "low", "high", NA), levels = c("low", "high"))

stopifnot(
    identical(typeof(value), "integer"),
    identical(class(value), "factor"),
    identical(levels(value), c("low", "high")),
    identical(unclass(value), structure(c(2L, 1L, 2L, NA_integer_), levels = c("low", "high"))),
    identical(as.character(value), c("high", "low", "high", NA_character_))
)
