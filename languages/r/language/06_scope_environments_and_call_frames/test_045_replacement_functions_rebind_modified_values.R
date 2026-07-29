# polyglot-covers: r.language.replacement-functions-primitives-and-call-frames

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

counter <- 0L
quoted <- quote({ counter <- counter + 1L; counter })
stopifnot(
    identical(typeof(mean), "closure"),
    identical(typeof(sum), "builtin"),
    identical(typeof(quote), "special"),
    is.primitive(sum),
    is.primitive(quote),
    identical(counter, 0L),
    identical(eval(quoted), 1L)
)

inspect_caller <- function() {
    list(marker = get("marker", envir = parent.frame(), inherits = FALSE), call = sys.call())
}
invoke <- function() {
    marker <- 42L
    inspect_caller()
}
frame <- invoke()
stopifnot(
    identical(frame$marker, 42L),
    identical(as.character(frame$call[[1L]]), "inspect_caller")
)

# replacement syntax 等价于调用 `name<-` 后把返回值重新绑定；parent.frame 则观察动态调用者。
