# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/r/language/07_vectors_recycling_and_subsetting/
# polyglot-related+: test_054_copy_on_modify_observable_value_semantics.R
#
# 共同问题：序列修改是否影响别名，遍历期间结构变化怎样处理。
# 对照观察：向量替换呈现值语义；`for` 的迭代序列在循环开始时确定，不暴露失效 iterator。

source <- 1:3
alias <- source
seen <- integer()
for (value in source) {
    seen <- c(seen, value)
    source <- c(source, 99L)
}

stopifnot(
    identical(seen, 1:3),
    identical(alias, 1:3),
    identical(source, c(1:3, 99L, 99L, 99L))
)
