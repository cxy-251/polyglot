# polyglot-covers: r.language.default-and-supplied-argument-environments

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
