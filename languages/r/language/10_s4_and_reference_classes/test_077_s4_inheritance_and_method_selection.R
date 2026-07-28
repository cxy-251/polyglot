# polyglot-covers: r.language.s4-inheritance-and-method-selection

methods::setClass("PolyglotShape", slots = c(name = "character"))
methods::setClass("PolyglotCircle", contains = "PolyglotShape", slots = c(radius = "numeric"))
methods::setGeneric("polyglot_name", function(x) standardGeneric("polyglot_name"))
methods::setMethod("polyglot_name", "PolyglotShape", function(x) paste("shape", x@name))

circle <- methods::new(
    "PolyglotCircle",
    name = "unit",
    radius = 1
)

stopifnot(
    methods::is(circle, "PolyglotCircle"),
    methods::is(circle, "PolyglotShape"),
    identical(polyglot_name(circle), "shape unit"),
    identical(
        unname(as.character(methods::selectMethod("polyglot_name", "PolyglotCircle")@defined)),
        "PolyglotShape"
    )
)
