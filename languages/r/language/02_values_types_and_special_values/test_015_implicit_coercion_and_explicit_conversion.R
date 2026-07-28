# polyglot-covers: r.language.implicit-coercion-and-explicit-conversion

mixed_numeric <- c(TRUE, 2L, 3.5)
mixed_text <- c(TRUE, 2L, "three")
preserved <- list(TRUE, 2L, "three")

stopifnot(
    identical(mixed_numeric, c(1, 2, 3.5)),
    identical(typeof(mixed_numeric), "double"),
    identical(mixed_text, c("TRUE", "2", "three")),
    identical(vapply(preserved, typeof, ""), c("logical", "integer", "character")),
    identical(as.integer("12"), 12L),
    is.na(suppressWarnings(as.integer("bad")))
)
