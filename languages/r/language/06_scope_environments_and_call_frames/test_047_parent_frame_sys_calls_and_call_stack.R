# polyglot-covers: r.language.parent-frame-sys-calls-and-call-stack

inspect_caller <- function() {
    list(
        marker = get("marker", envir = parent.frame(), inherits = FALSE),
        call = sys.call(),
        parents = sys.parents(),
        calls = sys.calls()
    )
}
invoke <- function() {
    marker <- 42L
    inspect_caller()
}

result <- invoke()
stopifnot(
    identical(result$marker, 42L),
    identical(as.character(result$call[[1L]]), "inspect_caller"),
    length(result$parents) >= 2L,
    identical(as.character(tail(result$calls, 1L)[[1L]][[1L]]), "inspect_caller")
)
