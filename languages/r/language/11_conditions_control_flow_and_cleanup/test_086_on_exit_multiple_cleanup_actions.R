# polyglot-covers: r.language.on-exit-multiple-cleanup-actions

trace <- character()
work <- function() {
    on.exit(trace <<- c(trace, "first"), add = TRUE)
    on.exit(trace <<- c(trace, "second"), add = TRUE)
    stop("failure")
}

error <- tryCatch(work(), error = identity)

stopifnot(
    inherits(error, "error"),
    identical(trace, c("first", "second"))
)
