# polyglot-covers: r.language.dispatch-does-not-force-unused-promises

polyglot_dispatch <- function(object, unused) UseMethod("polyglot_dispatch")
polyglot_dispatch.default <- function(object, unused) object$value

counter <- 0L
object <- structure(list(value = 7L), class = "polyglot_value")
result <- polyglot_dispatch(object, {
    counter <- counter + 1L
    stop("must remain lazy")
})

stopifnot(identical(result, 7L), counter == 0L)
