# polyglot-covers: r.language.s4-validity-and-invalid-construction

methods::setClass(
    "PolyglotRange",
    slots = c(lower = "numeric", upper = "numeric"),
    validity = function(object) {
        if (object@lower <= object@upper) TRUE else "lower exceeds upper"
    }
)

valid <- methods::new("PolyglotRange", lower = 1, upper = 3)
invalid <- tryCatch(
    methods::new("PolyglotRange", lower = 4, upper = 2),
    error = identity
)

stopifnot(
    identical(methods::validObject(valid), TRUE),
    inherits(invalid, "error"),
    grepl("lower exceeds upper", conditionMessage(invalid), fixed = TRUE)
)
