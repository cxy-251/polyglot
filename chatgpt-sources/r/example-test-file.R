values <- c(1, 2, 3)
doubled <- unlist(lapply(values, function(x) x * 2))

stopifnot(identical(doubled, c(2, 4, 6)))
stopifnot(identical(seq(1, 3), values))
