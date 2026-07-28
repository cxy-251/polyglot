# polyglot-covers: r.language.negative-logical-and-name-indices

value <- c(a = 10L, b = 20L, c = 30L, d = 40L)

stopifnot(
    identical(value[-c(1L, 4L)], c(b = 20L, c = 30L)),
    identical(value[c(TRUE, FALSE)], c(a = 10L, c = 30L)),
    identical(value[c("d", "a")], c(d = 40L, a = 10L)),
    identical(unname(value[0L]), integer(0)),
    identical(names(value[0L]), character(0)),
    inherits(tryCatch(value[c(-1L, 2L)], error = identity), "error")
)
