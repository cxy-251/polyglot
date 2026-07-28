# polyglot-covers: r.language.trycatch-exiting-handlers

trace <- character()
result <- tryCatch({
    trace <- c(trace, "before")
    stop("boom")
    trace <- c(trace, "unreachable")
}, error = function(condition) {
    trace <<- c(trace, paste("handler", conditionMessage(condition)))
    "recovered"
}, finally = {
    trace <- c(trace, "finally")
})

stopifnot(
    identical(result, "recovered"),
    identical(trace, c("before", "handler boom", "finally"))
)
