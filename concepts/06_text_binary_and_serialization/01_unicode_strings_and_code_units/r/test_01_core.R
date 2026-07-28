# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_099_csv_encodings_locale_and_regular_expressions.R
#
# 共同问题：字符串长度按字符、字节还是 code unit 计算；索引怎样处理 Unicode。
# 对照观察：R character 元素是字符串标量；`nchar` 显式选择 chars/bytes，`substr` 按字符位置。

text <- "Aé東京"

stopifnot(
    identical(nchar(text, type = "chars"), 4L),
    nchar(text, type = "bytes") > nchar(text, type = "chars"),
    identical(substr(text, 2L, 2L), "é"),
    identical(length(text), 1L),
    identical(Encoding(enc2utf8(text)), "UTF-8")
)
