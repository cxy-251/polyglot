# polyglot-covers: r.language.null-na-and-typed-missing-values

typed_missing <- list(NA, NA_integer_, NA_real_, NA_complex_, NA_character_)

stopifnot(
    is.null(NULL),
    length(NULL) == 0L,
    !is.null(NA),
    length(NA) == 1L,
    identical(vapply(typed_missing, typeof, ""), c(
        "logical", "integer", "double", "complex", "character"
    )),
    all(vapply(typed_missing, is.na, TRUE))
)
