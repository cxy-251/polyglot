# polyglot-covers: r.language.environment-manipulation-and-eval-scope

parent <- list2env(list(base = 10L), parent = baseenv())
child <- new.env(parent = parent)
child$increment <- 2L
expression <- quote(base + increment)

stopifnot(
    identical(eval(expression, child), 12L),
    identical(parent.env(child), parent),
    identical(environmentName(baseenv()), "base"),
    identical(ls(child, all.names = TRUE), "increment")
)
