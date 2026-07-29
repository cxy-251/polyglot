double_value <- function(value) {
    .Call(C_polyglot_double, as.double(value))
}

new_polyglot_label <- function(value) {
    structure(as.character(value), class = "polyglot_label")
}

print.polyglot_label <- function(x, ...) {
    cat("<polyglot_label>", unclass(x), "\n")
    invisible(x)
}

internal_identity <- function(value) value

.onLoad <- function(libname, pkgname) {
    invisible(c(libname, pkgname))
}

.onAttach <- function(libname, pkgname) {
    packageStartupMessage("polyglotrfixture attached")
}

.Last.lib <- function(libpath) {
    invisible(libpath)
}
