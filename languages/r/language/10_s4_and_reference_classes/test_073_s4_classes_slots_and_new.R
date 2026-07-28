# polyglot-covers: r.language.s4-classes-slots-and-new

methods::setClass("PolyglotPoint", slots = c(x = "numeric", y = "numeric"))
point <- methods::new("PolyglotPoint", x = 1, y = 2)

stopifnot(
    methods::is(point, "PolyglotPoint"),
    identical(methods::slotNames(point), c("x", "y")),
    identical(point@x, 1),
    identical(methods::slot(point, "y"), 2),
    methods::isClass("PolyglotPoint")
)
