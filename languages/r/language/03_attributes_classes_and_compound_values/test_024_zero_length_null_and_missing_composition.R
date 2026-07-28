# polyglot-covers: r.language.zero-length-null-and-missing-composition

stopifnot(
    identical(numeric(0) + 1, numeric(0)),
    identical(c(NULL, 1L), 1L),
    identical(list(NULL, integer(0), NA_integer_), list(NULL, integer(0), NA_integer_)),
    length(NULL) == 0L,
    length(integer(0)) == 0L,
    length(NA_integer_) == 1L,
    !is.na(NULL),
    identical(is.na(integer(0)), logical(0))
)
