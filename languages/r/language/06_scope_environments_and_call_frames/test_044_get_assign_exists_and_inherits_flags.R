# polyglot-covers: r.language.get-assign-exists-and-inherits-flags

parent <- new.env(parent = emptyenv())
child <- new.env(parent = parent)
assign("shared", 1L, envir = parent)
assign("local", 2L, envir = child)

stopifnot(
    identical(get("local", envir = child, inherits = FALSE), 2L),
    identical(get("shared", envir = child, inherits = TRUE), 1L),
    !exists("shared", envir = child, inherits = FALSE),
    exists("shared", envir = child, inherits = TRUE),
    identical(parent.env(child), parent)
)
