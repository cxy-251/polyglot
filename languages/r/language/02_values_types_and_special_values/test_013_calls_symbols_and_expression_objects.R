# polyglot-covers: r.language.calls-symbols-and-expression-objects

symbol <- as.name("value")
call <- quote(sum(value, 1L))
expressions <- expression(value <- 2L, value + 1L)

stopifnot(
    identical(typeof(symbol), "symbol"),
    identical(as.character(symbol), "value"),
    identical(typeof(call), "language"),
    identical(call[[1L]], as.name("sum")),
    identical(typeof(expressions), "expression"),
    length(expressions) == 2L
)
