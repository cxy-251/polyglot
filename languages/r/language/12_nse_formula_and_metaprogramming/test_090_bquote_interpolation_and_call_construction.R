# polyglot-covers: r.language.bquote-interpolation-and-call-construction

operation <- as.name("+")
right <- 2L
constructed <- bquote(.(operation)(1L, .(right)))
values <- list(1L, 2L)
interpolated <- bquote(list(.(values[[1L]]), .(values[[2L]]), 3L))

stopifnot(
    identical(constructed, quote(1L + 2L)),
    identical(eval(constructed), 3L),
    identical(eval(interpolated), list(1L, 2L, 3L)),
    is.call(constructed)
)
