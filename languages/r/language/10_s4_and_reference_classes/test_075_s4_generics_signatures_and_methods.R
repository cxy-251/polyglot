# polyglot-covers: r.language.s4-generics-signatures-and-methods

methods::setClass("PolyglotLabel", slots = c(value = "character"))
methods::setGeneric("polyglot_render", function(x, prefix = "") standardGeneric("polyglot_render"))
methods::setMethod(
    "polyglot_render",
    signature(x = "PolyglotLabel"),
    function(x, prefix = "") paste0(prefix, x@value)
)

value <- methods::new("PolyglotLabel", value = "R")

stopifnot(
    identical(polyglot_render(value), "R"),
    identical(polyglot_render(value, prefix = "language:"), "language:R"),
    methods::hasMethod("polyglot_render", "PolyglotLabel")
)
