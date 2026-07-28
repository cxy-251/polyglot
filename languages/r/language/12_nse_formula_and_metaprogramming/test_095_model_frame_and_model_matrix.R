# polyglot-covers: r.language.model-frame-and-model-matrix

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
