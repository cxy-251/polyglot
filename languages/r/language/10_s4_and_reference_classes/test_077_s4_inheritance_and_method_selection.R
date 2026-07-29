# polyglot-covers: r.language.s4-inheritance-method-selection-and-coercion

methods::setClass("PolyglotShape", slots = c(name = "character"))
methods::setClass("PolyglotCircle", contains = "PolyglotShape", slots = c(radius = "numeric"))
methods::setGeneric("polyglot_name", function(x) standardGeneric("polyglot_name"))
methods::setMethod("polyglot_name", "PolyglotShape", function(x) paste("shape", x@name))
methods::setClass("PolyglotShapeLabel", slots = c(value = "character"))
methods::setAs(
    "PolyglotCircle",
    "PolyglotShapeLabel",
    function(from) methods::new("PolyglotShapeLabel", value = from@name)
)

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
    ),
    identical(methods::as(circle, "PolyglotShapeLabel")@value, "unit"),
    methods::hasMethod("coerce", c("PolyglotCircle", "PolyglotShapeLabel")),
    !methods::hasMethod("coerce", c("PolyglotShapeLabel", "PolyglotCircle"))
)

# 继承让父类方法成为候选；setAs 注册方向明确的 coercion，不自动建立逆向转换。
