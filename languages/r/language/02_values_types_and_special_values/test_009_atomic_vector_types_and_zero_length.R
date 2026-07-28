# polyglot-covers: r.language.atomic-vector-types-and-zero-length

values <- list(
    logical = TRUE,
    integer = 1L,
    double = 1,
    complex = 1 + 2i,
    character = "R",
    raw = as.raw(0xff)
)

stopifnot(
    identical(unname(vapply(values, typeof, "")), names(values)),
    all(vapply(values, length, 0L) == 1L),
    identical(typeof(numeric()), "double"),
    length(numeric()) == 0L
)
