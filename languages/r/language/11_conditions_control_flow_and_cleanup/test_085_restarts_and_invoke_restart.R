# polyglot-covers: r.language.restarts-and-invoke-restart

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

stopifnot(
    identical(result, Inf),
    is.null(findRestart("use_value"))
)
