# polyglot-covers: r.language.stop-warning-message-and-signalcondition

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
