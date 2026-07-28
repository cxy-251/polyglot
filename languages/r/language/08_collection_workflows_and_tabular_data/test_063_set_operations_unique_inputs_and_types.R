# polyglot-covers: r.language.set-operations-unique-inputs-and-types

stopifnot(
    identical(union(c(1L, 1L, 2L), c(2L, 3L)), 1:3),
    identical(intersect(c("a", "b", "b"), c("b", "c")), "b"),
    identical(setdiff(c(1L, 2L, 3L), c(2L, 4L)), c(1L, 3L)),
    setequal(c(NA_integer_, 1L), c(1L, NA_integer_)),
    identical(unique(c(TRUE, TRUE, FALSE)), c(TRUE, FALSE))
)
