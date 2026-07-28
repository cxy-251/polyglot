# polyglot-covers: r.language.interrupt-conditions-and-cleanup

trace <- character()
work <- function() {
    on.exit(trace <<- c(trace, "cleanup"), add = TRUE)
    stop(structure(
        list(message = "interrupted", call = NULL),
        class = c("interrupt", "condition")
    ))
}

captured <- tryCatch(work(), interrupt = identity)

stopifnot(
    inherits(captured, "interrupt"),
    identical(conditionMessage(captured), "interrupted"),
    identical(trace, "cleanup")
)
