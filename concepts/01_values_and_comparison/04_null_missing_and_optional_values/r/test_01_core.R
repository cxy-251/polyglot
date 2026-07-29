# polyglot-family: values_and_comparison
# polyglot-concept: null_missing_and_optional_values
# polyglot-related: languages/r/language/02_values_types_and_special_values/
# polyglot-related+: test_009_atomic_vector_types_and_zero_length.R
#
# 共同问题：无值、缺失观测和可选字段如何区分。
# 对照观察：NULL 是长度零的无对象标记；NA 是带原子类型的缺失值并参与向量运算。

value <- list(present = NA_integer_, absent = 1L)
value$absent <- NULL

stopifnot(
    is.null(NULL),
    identical(length(NULL), 0L),
    identical(typeof(NA_integer_), "integer"),
    is.na(value$present),
    is.null(value$absent),
    !("absent" %in% names(value))
)
