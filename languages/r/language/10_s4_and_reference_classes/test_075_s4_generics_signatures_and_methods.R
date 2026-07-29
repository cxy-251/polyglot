# polyglot-covers: r.language.s4-generics-signatures-and-multiple-dispatch

methods::setClass("PolyglotLabel", slots = c(value = "character"))
methods::setClass("PolyglotPrefix", slots = c(value = "character"))
methods::setGeneric("polyglot_render", function(x, prefix = "") standardGeneric("polyglot_render"))
methods::setMethod(
    "polyglot_render",
    signature(x = "PolyglotLabel"),
    function(x, prefix = "") paste0(prefix, x@value)
)
methods::setMethod(
    "polyglot_render",
    signature(x = "PolyglotLabel", prefix = "PolyglotPrefix"),
    function(x, prefix) paste0(prefix@value, x@value)
)

value <- methods::new("PolyglotLabel", value = "R")
prefix <- methods::new("PolyglotPrefix", value = "language:")

stopifnot(
    identical(polyglot_render(value), "R"),
    identical(polyglot_render(value, prefix = "language:"), "language:R"),
    identical(polyglot_render(value, prefix), "language:R"),
    methods::hasMethod("polyglot_render", "PolyglotLabel"),
    methods::hasMethod("polyglot_render", c("PolyglotLabel", "PolyglotPrefix"))
)

# S4 generic 的 signature 可覆盖多个参数；method selection 比较每个实参的类距离。
