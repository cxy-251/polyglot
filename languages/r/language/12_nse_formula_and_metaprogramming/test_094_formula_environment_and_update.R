# polyglot-covers: r.language.formula-environment-and-update

environment <- new.env(parent = baseenv())
environment$offset <- 5
formula <- as.formula("response ~ predictor + offset", env = environment)
updated <- update(formula, . ~ . + I(predictor^2))

stopifnot(
    identical(environment(formula), environment),
    identical(environment(updated), environment),
    identical(all.vars(formula), c("response", "predictor", "offset")),
    identical(deparse1(updated), "response ~ predictor + offset + I(predictor^2)")
)
