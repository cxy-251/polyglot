# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/r/language/04_comparison_matching_and_ordering/
# polyglot-related+: test_032_set_operations_and_xtfrm_protocol.R
#
# 共同问题：key 计算失败如何传播，自定义顺序必须满足什么合同。
# 对照观察：S3 `xtfrm` 提供排序代理；方法错误直接传播，返回代理必须与对象长度一致。

xtfrm.polyglot_ranked <- function(x) {
    if (anyNA(unclass(x))) stop("missing rank")
    -unclass(x)
}
value <- structure(c(1, 3, 2), class = "polyglot_ranked")
invalid <- structure(c(1, NA), class = "polyglot_ranked")

stopifnot(
    identical(order(xtfrm.polyglot_ranked(value)), c(2L, 3L, 1L)),
    inherits(tryCatch(xtfrm.polyglot_ranked(invalid), error = identity), "error")
)
