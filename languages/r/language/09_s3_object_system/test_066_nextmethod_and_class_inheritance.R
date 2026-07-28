# polyglot-covers: r.language.s3-nextmethod-and-class-inheritance

render <- function(x, ...) UseMethod("render")
render.default <- function(x, ...) paste0("default:", unclass(x))
render.parent <- function(x, ...) paste0("parent(", NextMethod(), ")")
render.child <- function(x, ...) paste0("child(", NextMethod(), ")")

value <- structure(7L, class = c("child", "parent"))

stopifnot(
    identical(render(value), "child(parent(default:7))"),
    inherits(value, "child"),
    inherits(value, "parent"),
    !inherits(value, "unrelated")
)
