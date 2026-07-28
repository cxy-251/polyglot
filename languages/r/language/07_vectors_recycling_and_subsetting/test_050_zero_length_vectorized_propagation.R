# polyglot-covers: r.language.zero-length-vectorized-propagation

stopifnot(
    identical(integer(0) + 1L, integer(0)),
    identical(logical(0) & TRUE, logical(0)),
    identical(paste0(character(0), "suffix"), "suffix"),
    identical(paste0(character(0), "suffix", recycle0 = TRUE), character(0)),
    identical(ifelse(logical(0), 1L, 2L), logical(0)),
    identical(rep(1L, times = 0L), integer(0)),
    identical(seq_along(NULL), integer(0))
)
