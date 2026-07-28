# polyglot-covers: r.language.withcallinghandlers-observes-in-place

trace <- character()
result <- withCallingHandlers({
    trace <- c(trace, "before")
    signalCondition(structure(
        list(message = "event", call = NULL),
        class = c("polyglot_notice", "condition")
    ))
    trace <- c(trace, "after")
    42L
}, polyglot_notice = function(condition) {
    trace <<- c(trace, paste("handler", conditionMessage(condition)))
})

stopifnot(
    identical(result, 42L),
    identical(trace, c("before", "handler event", "after"))
)
