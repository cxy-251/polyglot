# polyglot-family: values_and_comparison
# polyglot-concept: numeric_models_and_conversion
# polyglot-related: languages/r/language/02_values_types_and_special_values/
# polyglot-related+: test_015_implicit_coercion_and_explicit_conversion.R
#
# 共同问题：整数、浮点数与复数怎样表示和转换；失败是否静默。
# 对照观察：R 的 numeric 通常是 double；混合原子向量提升类型，失败转换产生带 warning 的 NA。

warning_value <- NULL
converted <- withCallingHandlers(
    as.integer("not-a-number"),
    warning = function(condition) {
        warning_value <<- condition
        invokeRestart("muffleWarning")
    }
)

stopifnot(
    identical(typeof(1L), "integer"),
    identical(typeof(1), "double"),
    identical(typeof(c(1L, 2.5)), "double"),
    is.na(converted),
    inherits(warning_value, "warning")
)
