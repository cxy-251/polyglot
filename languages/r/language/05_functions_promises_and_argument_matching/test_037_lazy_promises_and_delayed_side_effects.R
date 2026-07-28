# polyglot-covers: r.language.lazy-promises-and-delayed-side-effects

counter <- 0L
ignore <- function(value) "ignored"
force_once <- function(value) value

stopifnot(identical(ignore({ counter <- counter + 1L; 10L }), "ignored"))
stopifnot(counter == 0L)

result <- force_once({
    counter <- counter + 1L
    10L
})
stopifnot(identical(result, 10L), counter == 1L)
