# polyglot-covers: r.language.s3-group-generics

new_distance <- function(value) structure(value, class = "distance")
Ops.distance <- function(e1, e2) {
    left <- unclass(e1)
    right <- if (inherits(e2, "distance")) unclass(e2) else e2
    switch(.Generic,
        "+" = new_distance(left + right),
        "==" = left == right,
        stop("unsupported distance operation")
    )
}
Summary.distance <- function(..., na.rm = FALSE) {
    values <- lapply(list(...), unclass)
    do.call(.Generic, c(values, list(na.rm = na.rm)))
}

first <- new_distance(c(1, 2))
second <- new_distance(c(3, 4))

stopifnot(
    identical(unclass(first + second), c(4, 6)),
    identical(first == new_distance(c(1, 9)), c(TRUE, FALSE)),
    identical(sum(first, second), 10)
)
