# polyglot-covers: r.language.formula-capture-and-environment

offset <- 10
formula <- response ~ predictor + offset

stopifnot(
    inherits(formula, "formula"),
    identical(typeof(formula), "language"),
    identical(environment(formula), environment()),
    identical(formula[[2L]], as.name("response")),
    identical(formula[[3L]], quote(predictor + offset)),
    identical(eval(as.name("offset"), environment(formula)), 10)
)
