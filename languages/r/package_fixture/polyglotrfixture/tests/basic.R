library(polyglotrfixture)

stopifnot(
    identical(double_value(c(1, 2)), c(2, 4)),
    inherits(new_polyglot_label("R"), "polyglot_label")
)
