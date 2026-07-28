# polyglot-covers: r.language.value-identity-and-approximate-equality

left <- c(a = 1, b = 2)
right <- c(a = 1, b = 2)
different_attributes <- unname(right)

stopifnot(
    all(left == right),
    identical(left, right),
    !identical(left, different_attributes),
    isTRUE(all.equal(left, different_attributes, check.attributes = FALSE)),
    is.character(all.equal(left, different_attributes))
)
