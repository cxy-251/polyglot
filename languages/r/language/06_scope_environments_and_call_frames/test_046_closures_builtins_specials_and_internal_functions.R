# polyglot-covers: r.language.closures-builtins-specials-and-internal-functions

counter <- 0L
quoted <- quote({ counter <- counter + 1L; counter })

stopifnot(
    identical(typeof(mean), "closure"),
    identical(typeof(sum), "builtin"),
    identical(typeof(quote), "special"),
    is.primitive(sum),
    is.primitive(quote),
    identical(counter, 0L),
    identical(eval(quoted), 1L),
    identical(counter, 1L)
)
