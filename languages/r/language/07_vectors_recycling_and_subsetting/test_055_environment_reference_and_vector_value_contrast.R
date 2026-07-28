# polyglot-covers: r.language.environment-reference-and-vector-value-contrast

vector <- 1:2
vector_alias <- vector
vector_alias[1L] <- 9L

environment_value <- new.env(parent = emptyenv())
environment_value$count <- 1L
environment_alias <- environment_value
environment_alias$count <- 2L

stopifnot(
    identical(vector, 1:2),
    identical(vector_alias, c(9L, 2L)),
    identical(environment_value$count, 2L),
    identical(environment_value, environment_alias)
)
