# polyglot-covers: r.language.s3-constructors-validators-and-malformed-objects

validate_percentage <- function(x) {
    if (!is.double(x) || anyNA(x) || any(x < 0 | x > 100)) {
        stop("invalid percentage")
    }
    x
}
new_percentage <- function(x) {
    structure(validate_percentage(as.double(x)), class = "percentage")
}

valid <- new_percentage(c(25, 50))
malformed <- structure("not numeric", class = "percentage")

stopifnot(
    identical(unclass(valid), c(25, 50)),
    inherits(malformed, "percentage"),
    identical(typeof(malformed), "character"),
    inherits(tryCatch(validate_percentage(malformed), error = identity), "error")
)
