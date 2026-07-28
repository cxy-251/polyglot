# polyglot-covers: r.language.first-class-functions-and-closure-components

offset <- 3L
add_offset <- function(value = 1L) value + offset
functions <- list(add_offset, identity)

stopifnot(
    identical(typeof(add_offset), "closure"),
    identical(formals(add_offset), pairlist(value = 1L)),
    identical(body(add_offset), quote(value + offset)),
    identical(environment(add_offset), environment()),
    identical(functions[[1L]](4L), 7L),
    identical(functions[[2L]]("value"), "value")
)
