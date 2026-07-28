# polyglot-covers: r.language.s4-multiple-dispatch

methods::setClass("PolyglotScalar", slots = c(value = "numeric"))
methods::setClass("PolyglotVector", slots = c(value = "numeric"))
methods::setGeneric("polyglot_combine", function(x, y) standardGeneric("polyglot_combine"))
methods::setMethod(
    "polyglot_combine",
    c("PolyglotScalar", "PolyglotVector"),
    function(x, y) x@value + y@value
)
methods::setMethod(
    "polyglot_combine",
    c("PolyglotVector", "PolyglotScalar"),
    function(x, y) x@value * y@value
)

scalar <- methods::new("PolyglotScalar", value = 2)
vector <- methods::new("PolyglotVector", value = c(3, 4))

stopifnot(
    identical(polyglot_combine(scalar, vector), c(5, 6)),
    identical(polyglot_combine(vector, scalar), c(6, 8))
)
