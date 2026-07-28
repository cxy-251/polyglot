# polyglot-covers: r.language.nan-infinity-and-complex-values

stopifnot(
    is.nan(NaN),
    is.na(NaN),
    !is.nan(NA_real_),
    is.infinite(c(Inf, -Inf)),
    identical(1 / 0, Inf),
    identical(typeof(1 + 2i), "complex"),
    identical(Re(1 + 2i), 1),
    identical(Im(1 + 2i), 2)
)
