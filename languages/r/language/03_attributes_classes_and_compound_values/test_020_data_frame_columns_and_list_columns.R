# polyglot-covers: r.language.data-frame-columns-and-list-columns

frame <- data.frame(
    id = 1:2,
    label = c("one", "two"),
    payload = I(list(list(value = 1L), list(value = 2L)))
)

stopifnot(
    inherits(frame, "data.frame"),
    identical(dim(frame), c(2L, 3L)),
    identical(typeof(frame), "list"),
    identical(typeof(frame$label), "character"),
    inherits(frame$payload, "AsIs"),
    identical(frame$payload[[2L]]$value, 2L)
)
