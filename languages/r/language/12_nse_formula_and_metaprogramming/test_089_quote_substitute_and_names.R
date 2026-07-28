# polyglot-covers: r.language.quote-substitute-and-names

capture <- function(argument) {
    list(expression = substitute(argument), name = deparse1(substitute(argument)))
}

value <- 42L
captured <- capture(value + 1L)

stopifnot(
    identical(quote(value + 1L), captured$expression),
    identical(captured$name, "value + 1L"),
    identical(as.name("value"), quote(value)),
    identical(typeof(quote(value)), "symbol")
)
