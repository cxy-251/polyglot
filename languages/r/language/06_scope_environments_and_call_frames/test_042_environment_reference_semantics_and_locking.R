# polyglot-covers: r.language.environment-reference-semantics-and-locking

state <- new.env(parent = emptyenv())
state$count <- 1L
alias <- state
alias$count <- 2L
lockEnvironment(state, bindings = FALSE)

stopifnot(
    identical(state, alias),
    identical(state$count, 2L),
    environmentIsLocked(state),
    !bindingIsLocked("count", state),
    inherits(tryCatch(state$new <- 1L, error = identity), "error")
)
