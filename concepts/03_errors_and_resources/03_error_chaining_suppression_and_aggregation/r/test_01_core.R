# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_087_nested_failures_and_condition_context.R
#
# 共同问题：包装错误时如何保留 cause；如何显式隐藏或替换上下文。
# 对照观察：base R condition 没有自动 chaining 语法，应用可在自定义 condition 字段中保存 parent。

inner <- simpleError("decode")
outer <- errorCondition("load", class = "polyglot_wrapped", parent = inner)
captured <- tryCatch(stop(outer), polyglot_wrapped = identity)

stopifnot(
    identical(conditionMessage(captured), "load"),
    identical(conditionMessage(captured$parent), "decode"),
    inherits(captured$parent, "error")
)
