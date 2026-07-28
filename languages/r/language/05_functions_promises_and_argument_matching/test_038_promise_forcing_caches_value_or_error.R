# polyglot-covers: r.language.promise-forcing-caches-value-or-error

counter <- 0L
twice <- function(value) c(value, value)

result <- twice({
    counter <- counter + 1L
    counter
})

stopifnot(identical(result, c(1L, 1L)), counter == 1L)

failure_counter <- 0L
failure <- tryCatch(
    twice({ failure_counter <- failure_counter + 1L; stop("forced") }),
    error = identity
)
stopifnot(inherits(failure, "error"), failure_counter == 1L)
