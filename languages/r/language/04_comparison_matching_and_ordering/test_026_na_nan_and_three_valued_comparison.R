# polyglot-covers: r.language.na-nan-and-three-valued-comparison

stopifnot(
    is.na(NA == NA),
    is.na(NaN == NaN),
    identical(NA, NA),
    identical(NaN, NaN),
    is.na(NA_real_),
    !is.nan(NA_real_),
    is.nan(NaN),
    identical(is.na(c(1, NA, NaN)), c(FALSE, TRUE, TRUE))
)
