# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/r/language/05_functions_promises_and_argument_matching/
# polyglot-related+: test_037_lazy_promises_and_delayed_side_effects.R
#
# 共同问题：元素能否按需产生，消费者怎样提前终止。
# 对照观察：base R 没有 yield generator；lazy promise 延迟整个表达式，循环用 `break` 提前停止。

forced <- FALSE
delayedAssign("values", {
    forced <- TRUE
    1:5
})
stopifnot(!forced)
seen <- integer()
for (value in values) {
    if (value > 2L) break
    seen <- c(seen, value)
}

stopifnot(forced, identical(seen, 1:2))
