# polyglot-covers: r.tooling.stopifnot-and-condition-assertions

stopifnot(1L + 1L == 2L, identical(TRUE, isTRUE(1 < 2)))

failure <- tryCatch(
    {
        stopifnot(FALSE)
        NULL
    },
    error = identity
)
stopifnot(inherits(failure, "error"), grepl("FALSE", conditionMessage(failure), fixed = TRUE))
