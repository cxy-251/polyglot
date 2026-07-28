# polyglot-covers: r.language.s4-method-introspection-and-ambiguity

methods::setClass("PolyglotLeft", slots = c(value = "logical"))
methods::setClass("PolyglotRight", slots = c(value = "logical"))
methods::setGeneric("polyglot_route", function(x, y) standardGeneric("polyglot_route"))
methods::setMethod("polyglot_route", c("PolyglotLeft", "ANY"), function(x, y) "left")
methods::setMethod("polyglot_route", c("ANY", "PolyglotRight"), function(x, y) "right")

left <- methods::new("PolyglotLeft", value = TRUE)
right <- methods::new("PolyglotRight", value = TRUE)
selection <- suppressMessages(suppressWarnings(
    methods::selectMethod(
        "polyglot_route",
        c("PolyglotLeft", "PolyglotRight"),
        optional = TRUE
    )
))

stopifnot(
    is.function(selection),
    methods::hasMethod("polyglot_route", c("PolyglotLeft", "ANY")),
    methods::hasMethod("polyglot_route", c("ANY", "PolyglotRight")),
    polyglot_route(left, 1L) == "left",
    polyglot_route(1L, right) == "right"
)
