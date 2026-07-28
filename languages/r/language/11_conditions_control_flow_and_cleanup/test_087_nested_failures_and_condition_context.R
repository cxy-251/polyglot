# polyglot-covers: r.language.nested-failures-and-condition-context

inner <- simpleError("inner failure")
outer <- errorCondition(
    "outer failure",
    class = "polyglot_wrapped_error",
    parent = inner,
    operation = "load"
)
captured <- tryCatch(stop(outer), polyglot_wrapped_error = identity)

stopifnot(
    identical(conditionMessage(captured), "outer failure"),
    identical(captured$operation, "load"),
    inherits(captured$parent, "error"),
    identical(conditionMessage(captured$parent), "inner failure")
)
