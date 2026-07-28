# polyglot-covers: r.language.eval-environments-and-list-data-masks

lexical <- new.env(parent = baseenv())
lexical$x <- 10L
mask <- list(x = 2L, y = 3L)

stopifnot(
    identical(eval(quote(x + y), envir = mask, enclos = baseenv()), 5L),
    identical(eval(quote(x), envir = lexical), 10L),
    inherits(
        tryCatch(eval(quote(x + y), envir = mask, enclos = emptyenv()), error = identity),
        "error"
    ),
    identical(evalq(x <- x + 1L, envir = lexical), 11L),
    identical(lexical$x, 11L)
)
