# polyglot-covers: r.language.conditions-exiting-and-calling-handlers

warning_value <- tryCatch({
    warning("careful")
    NULL
}, warning = identity)
message_value <- tryCatch({
    message("note")
    NULL
}, message = identity)
custom <- structure(
    list(message = "event", call = NULL, code = 7L),
    class = c("polyglot_event", "condition")
)
custom_value <- tryCatch(signalCondition(custom), polyglot_event = identity)
error_value <- tryCatch(stop("failed"), error = identity)

stopifnot(
    inherits(warning_value, "warning"),
    inherits(message_value, "message"),
    identical(custom_value$code, 7L),
    inherits(error_value, "error")
)

exiting_trace <- character()
exiting_result <- tryCatch({
    exiting_trace <- c(exiting_trace, "before")
    stop("boom")
}, error = function(condition) {
    exiting_trace <<- c(exiting_trace, "handler")
    "recovered"
}, finally = {
    exiting_trace <- c(exiting_trace, "finally")
})

calling_trace <- character()
calling_result <- withCallingHandlers({
    calling_trace <- c(calling_trace, "before")
    signalCondition(custom)
    calling_trace <- c(calling_trace, "after")
    42L
}, polyglot_event = function(condition) {
    calling_trace <<- c(calling_trace, paste0("handler:", condition$code))
})

stopifnot(
    identical(exiting_result, "recovered"),
    identical(exiting_trace, c("before", "handler", "finally")),
    identical(calling_result, 42L),
    identical(calling_trace, c("before", "handler:7", "after"))
)

# tryCatch handler 从建立点退出；withCallingHandlers handler 在 signal 点调用，返回后继续原计算。
