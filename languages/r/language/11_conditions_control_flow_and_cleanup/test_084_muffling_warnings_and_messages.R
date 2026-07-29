# polyglot-covers: r.language.muffling-and-restarts

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

divide <- function(numerator, denominator) {
    withRestarts({
        if (denominator == 0) {
            signalCondition(structure(
                list(message = "zero denominator", call = NULL),
                class = c("polyglot_zero", "condition")
            ))
        }
        numerator / denominator
    }, use_value = function(value) value)
}
result <- withCallingHandlers(
    divide(10, 0),
    polyglot_zero = function(condition) invokeRestart("use_value", Inf)
)
stopifnot(identical(result, Inf), is.null(findRestart("use_value")))

# warning/message 自带 muffle restart；业务条件可由建立者用 withRestarts 提供恢复协议。
