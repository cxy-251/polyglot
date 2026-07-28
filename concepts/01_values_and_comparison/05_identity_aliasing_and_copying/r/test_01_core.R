# polyglot-family: values_and_comparison
# polyglot-concept: identity_aliasing_and_copying
# polyglot-related: languages/r/language/07_vectors_recycling_and_subsetting/
# polyglot-related+: test_055_environment_reference_and_vector_value_contrast.R
#
# 共同问题：赋值后两个名字共享身份还是独立值；修改如何可见。
# 对照观察：普通向量呈现 copy-on-modify 值语义；environment 保持可观察的引用别名。

vector <- c(1L, 2L)
vector_alias <- vector
vector[1L] <- 9L
environment <- new.env(parent = emptyenv())
environment$value <- 1L
environment_alias <- environment
environment_alias$value <- 9L

stopifnot(
    identical(vector_alias, c(1L, 2L)),
    identical(environment$value, 9L),
    identical(environment, environment_alias)
)
