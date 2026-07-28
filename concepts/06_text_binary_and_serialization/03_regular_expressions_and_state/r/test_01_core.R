# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_099_csv_encodings_locale_and_regular_expressions.R
#
# 共同问题：匹配、捕获和全局搜索怎样返回位置与状态。
# 对照观察：R regex 函数是向量化调用，没有可变 lastIndex；match 对象携带捕获位置属性。

match <- regexec("([[:alpha:]]+)-([[:digit:]]+)", "item-42", perl = TRUE)
parts <- regmatches("item-42", match)[[1L]]
all_digits <- regmatches("a1b22", gregexpr("[[:digit:]]+", "a1b22"))[[1L]]

stopifnot(
    identical(parts, c("item-42", "item", "42")),
    identical(all_digits, c("1", "22")),
    identical(unname(attr(match[[1L]], "match.length")), c(7L, 4L, 2L))
)
