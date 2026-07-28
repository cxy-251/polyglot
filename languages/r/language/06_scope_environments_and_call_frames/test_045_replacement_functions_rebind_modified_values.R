# polyglot-covers: r.language.replacement-functions-rebind-modified-values

unit <- function(x) attr(x, "unit", exact = TRUE)
`unit<-` <- function(x, value) {
    attr(x, "unit") <- value
    x
}

measurement <- 1:3
alias <- measurement
unit(measurement) <- "kg"

stopifnot(
    identical(unit(measurement), "kg"),
    is.null(unit(alias)),
    identical(unclass(measurement), structure(1:3, unit = "kg")),
    identical(alias, 1:3)
)
