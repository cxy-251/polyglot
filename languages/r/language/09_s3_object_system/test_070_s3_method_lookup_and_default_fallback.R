# polyglot-covers: r.language.s3-method-lookup-and-default-fallback

identify <- function(x) UseMethod("identify")
identify.default <- function(x) "default"
identify.second <- function(x) "second"

both <- structure(1L, class = c("first", "second"))
only_unknown <- structure(2L, class = "unknown")

stopifnot(
    identical(identify(both), "second"),
    identical(identify(only_unknown), "default"),
    identical(getS3method("identify", "second"), identify.second),
    is.null(getS3method("identify", "missing", optional = TRUE))
)
