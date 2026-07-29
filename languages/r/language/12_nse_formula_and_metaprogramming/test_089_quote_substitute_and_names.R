# polyglot-covers: r.language.quote-substitute-bquote-and-match-call

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

operation <- as.name("+")
right <- 2L
constructed <- bquote(.(operation)(1L, .(right)))
stopifnot(
    identical(constructed, quote(1L + 2L)),
    identical(eval(constructed), 3L),
    is.call(constructed)
)

normalize <- function(alpha, beta = 2L, ..., expand = TRUE) match.call(expand.dots = expand)
expanded <- normalize(be = 4L, alpha = 1L, extra = 9L)
packed <- normalize(be = 4L, alpha = 1L, extra = 9L, expand = FALSE)
stopifnot(
    identical(expanded$beta, 4L),
    identical(expanded$extra, 9L),
    is.pairlist(packed$...),
    identical(packed$...$extra, 9L)
)

# substitute 捕获 promise 表达式；bquote 显式插值；match.call 采用函数的真实参数匹配规则。
