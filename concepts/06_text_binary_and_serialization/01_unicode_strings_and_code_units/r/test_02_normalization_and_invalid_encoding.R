# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_099_csv_encodings_locale_and_regular_expressions.R
#
# 共同问题：规范等价文本是否自动相等，非法编码怎样处理。
# 对照观察：base R 不自动做 Unicode normalization；`iconv` 可把不可转换输入替换或返回 NA。

composed <- "\u00e9"
decomposed <- "e\u0301"
invalid <- rawToChar(as.raw(c(0xc3, 0x28)))
converted <- iconv(invalid, from = "UTF-8", to = "UTF-8", sub = NA)

stopifnot(
    !identical(composed, decomposed),
    is.na(converted),
    identical(nchar(composed, type = "chars"), 1L),
    identical(nchar(decomposed, type = "chars"), 2L)
)
