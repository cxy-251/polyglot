# polyglot-covers: r.language.s4-classes-slots-and-validity

methods::setClass(
    "PolyglotPoint",
    slots = c(x = "numeric", y = "numeric"),
    validity = function(object) {
        if (length(object@x) == 1L && length(object@y) == 1L) TRUE else "coordinates must be scalar"
    }
)
point <- methods::new("PolyglotPoint", x = 1, y = 2)
invalid <- tryCatch(methods::new("PolyglotPoint", x = c(1, 2), y = 3), error = identity)

stopifnot(
    methods::is(point, "PolyglotPoint"),
    identical(methods::slotNames(point), c("x", "y")),
    identical(point@x, 1),
    identical(methods::slot(point, "y"), 2),
    methods::isClass("PolyglotPoint"),
    identical(methods::validObject(point), TRUE),
    inherits(invalid, "error")
)

# slot 类型约束与 validity 约束是两层检查；new() 完成后调用有效性检查。
