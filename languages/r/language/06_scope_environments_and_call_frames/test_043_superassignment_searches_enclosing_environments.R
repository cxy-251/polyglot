# polyglot-covers: r.language.superassignment-searches-enclosing-environments

factory <- function() {
    value <- 1L
    list(
        read = function() value,
        update = function() {
            value <<- value + 1L
            value
        }
    )
}

state <- factory()

stopifnot(
    identical(state$read(), 1L),
    identical(state$update(), 2L),
    identical(state$read(), 2L),
    !exists("value", envir = environment(), inherits = FALSE)
)
