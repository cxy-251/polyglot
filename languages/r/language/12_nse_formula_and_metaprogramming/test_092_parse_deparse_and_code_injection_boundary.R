# polyglot-covers: r.language.parse-deparse-and-code-injection-boundary

text <- "x + 2L"
expression <- parse(text = text, keep.source = FALSE)
safe_environment <- list2env(list(x = 3L), parent = baseenv())
untrusted <- "stop('injected')"
parsed_untrusted <- parse(text = untrusted, keep.source = FALSE)

stopifnot(
    identical(eval(expression, safe_environment), 5L),
    identical(deparse1(expression[[1L]]), text),
    is.expression(parsed_untrusted),
    inherits(tryCatch(eval(parsed_untrusted, safe_environment), error = identity), "error")
)
