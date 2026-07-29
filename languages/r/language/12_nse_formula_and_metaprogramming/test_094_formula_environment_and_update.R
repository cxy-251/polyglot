# polyglot-covers: r.language.formula-environments-and-model-matrices

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

data <- data.frame(
    response = c(1, 2, 3),
    group = factor(c("a", "b", "a"), levels = c("a", "b"))
)
frame <- stats::model.frame(response ~ group, data = data)
matrix <- stats::model.matrix(response ~ group, data = frame)
stopifnot(
    identical(names(frame), c("response", "group")),
    identical(colnames(matrix), c("(Intercept)", "groupb")),
    identical(unname(matrix[, "groupb"]), c(0, 1, 0)),
    identical(attr(terms(frame), "response"), 1L)
)

# formula 捕获环境；model.frame 在 data 与 formula 环境中解析变量，model.matrix 再展开 contrasts。
