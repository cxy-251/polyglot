# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_099_csv_encodings_locale_and_regular_expressions.R
#
# 共同问题：零宽匹配怎样前进，非法模式和无匹配怎样表达。
# 对照观察：`gregexpr` 返回位置向量；无匹配用 -1，非法 PCRE 模式发出 error。

zero_width <- gregexpr("(?=a)", "aa", perl = TRUE)[[1L]]
missing <- regexpr("z", "aa", fixed = TRUE)
invalid <- tryCatch(grepl("(", "text", perl = TRUE), error = identity)

stopifnot(
    identical(as.integer(zero_width), c(1L, 2L)),
    identical(as.integer(missing), -1L),
    inherits(invalid, "error")
)
