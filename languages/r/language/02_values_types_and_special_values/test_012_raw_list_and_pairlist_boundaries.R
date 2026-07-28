# polyglot-covers: r.language.raw-list-and-pairlist-boundaries

bytes <- charToRaw("R")
heterogeneous <- list(1L, "two", NULL)
arguments <- pairlist(first = 1L, second = quote(value))

stopifnot(
    identical(bytes, as.raw(0x52)),
    identical(typeof(heterogeneous), "list"),
    length(heterogeneous) == 3L,
    identical(typeof(arguments), "pairlist"),
    identical(arguments[[2L]], quote(value)),
    identical(pairlist(), NULL)
)
