# polyglot-covers: r.language.lexical-scoping-and-closure-state

make_counter <- function() {
    value <- 0L
    function() {
        value <<- value + 1L
        value
    }
}

first <- make_counter()
second <- make_counter()

stopifnot(
    identical(c(first(), first(), second()), c(1L, 2L, 1L)),
    !identical(environment(first), environment(second)),
    identical(parent.env(environment(first)), environment(make_counter))
)
