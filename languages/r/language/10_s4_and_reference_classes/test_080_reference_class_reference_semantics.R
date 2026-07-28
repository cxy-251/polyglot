# polyglot-covers: r.language.reference-class-reference-semantics

Counter <- methods::setRefClass(
    "PolyglotCounter",
    fields = list(value = "numeric"),
    methods = list(
        increment = function(amount = 1) {
            value <<- value + amount
            value
        }
    )
)

first <- Counter$new(value = 0)
alias <- first
copy <- first$copy()
first$increment(2)

stopifnot(
    identical(alias$value, 2),
    identical(copy$value, 0),
    identical(first, alias),
    !identical(first, copy)
)
