# polyglot-covers: r.language.muffling-warnings-and-messages

warnings <- character()
messages <- character()
output <- capture.output(
    withCallingHandlers({
        warning("quiet warning")
        message("quiet message")
        invisible("done")
    },
    warning = function(condition) {
        warnings <<- c(warnings, conditionMessage(condition))
        invokeRestart("muffleWarning")
    },
    message = function(condition) {
        messages <<- c(messages, conditionMessage(condition))
        invokeRestart("muffleMessage")
    }),
    type = "message"
)

stopifnot(
    identical(warnings, "quiet warning"),
    identical(trimws(messages), "quiet message"),
    identical(output, character(0))
)
