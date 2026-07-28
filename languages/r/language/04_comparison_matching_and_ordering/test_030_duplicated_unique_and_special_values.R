# polyglot-covers: r.language.duplicated-unique-and-special-values

values <- c(1, 1, NA_real_, NA_real_, NaN, NaN, -0, 0)

stopifnot(
    identical(duplicated(values), c(FALSE, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, TRUE)),
    identical(unique(values), c(1, NA_real_, NaN, 0)),
    identical(anyDuplicated(values), 2L),
    identical(anyDuplicated(c("a", "b")), 0L)
)
