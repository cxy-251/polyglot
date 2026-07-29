# polyglot-family: objects_and_dispatch
# polyglot-concept: member_attribute_lookup_and_properties
# polyglot-related: languages/r/language/02_values_types_and_special_values/
# polyglot-related+: test_015_implicit_coercion_and_explicit_conversion.R
#
# 共同问题：成员、属性和计算属性如何查找。
# 对照观察：list/environment 用 `$`，S4 用 slot；attributes 是对象元数据而非统一成员描述符。

record <- list(value = 42L)
attr(record, "unit") <- "kg"
environment <- list2env(list(value = 42L), parent = emptyenv())

stopifnot(
    identical(record$value, 42L),
    identical(attr(record, "unit"), "kg"),
    identical(environment$value, 42L),
    is.null(record$missing)
)
