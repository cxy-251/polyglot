# polyglot-family: values_and_comparison
# polyglot-concept: truthiness
# polyglot-related: languages/r/language/02_values_types_and_special_values/
# polyglot-related+: test_009_atomic_vector_types_and_zero_length.R
#
# 共同问题：零、空集合、缺失值怎样进入条件；逻辑运算接受什么输入。
# 对照观察：R 条件要求长度一且非 NA；数值零可转为 FALSE，长度零和 NA 会失败。

stopifnot(
    identical(if (0) "yes" else "no", "no"),
    identical(if (1) "yes" else "no", "yes"),
    inherits(tryCatch(if (logical(0)) 1L, error = identity), "error"),
    inherits(tryCatch(if (NA) 1L, error = identity), "error")
)
