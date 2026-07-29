# polyglot-covers: r.language.promise-environments-forcing-and-retry

reader <- local({
    value <- "definition"
    function(argument = value) argument
})

value <- "caller"
supplied <- local({
    value <- "actual"
    reader(value)
})

stopifnot(
    identical(reader(), "definition"),
    identical(reader(value), "caller"),
    identical(supplied, "actual"),
    identical(value, "caller")
)

counter <- 0L
twice <- function(argument) c(argument, argument)
result <- twice({
    counter <- counter + 1L
    counter
})
stopifnot(identical(result, c(1L, 1L)), counter == 1L)

# 成功强制会缓存值；失败不会缓存为永久结果，再次访问会重新求值并发出 restart warning。
failure_counter <- 0L
retry <- function(argument) {
    first <- tryCatch(argument, error = identity)
    second <- suppressWarnings(tryCatch(argument, error = identity))
    list(first, second)
}
failures <- retry({
    failure_counter <- failure_counter + 1L
    stop(structure(
        list(message = "forced", call = NULL, attempt = failure_counter),
        class = c("polyglot_force_error", "error", "condition")
    ))
})
stopifnot(
    all(vapply(failures, inherits, logical(1), "polyglot_force_error")),
    identical(vapply(failures, `[[`, integer(1), "attempt"), 1:2),
    failure_counter == 2L
)
