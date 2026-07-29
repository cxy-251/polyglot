# polyglot-covers: r.language.eval-data-masks-and-environment-chains

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

parent <- list2env(list(base = 10L), parent = baseenv())
child <- new.env(parent = parent)
child$increment <- 2L
stopifnot(
    identical(eval(quote(base + increment), child), 12L),
    identical(parent.env(child), parent),
    identical(ls(child, all.names = TRUE), "increment")
)

# list data mask 的 fallback 由 enclos 指定；environment 则直接通过 enclosure 形成词法查询链。
