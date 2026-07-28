# polyglot-family: text_binary_and_serialization
# polyglot-concept: formatting_parsing_and_interpolation
# polyglot-related: languages/r/language/12_nse_formula_and_metaprogramming/
# polyglot-related+: test_092_parse_deparse_and_code_injection_boundary.R
#
# 共同问题：值怎样格式化、文本怎样解析，插值是否执行代码。
# 对照观察：`sprintf`/`format` 格式化值；`parse` 生成 language object，只有显式 `eval` 才执行。

expression <- parse(text = "1L + 2L", keep.source = FALSE)

stopifnot(
    identical(sprintf("%s:%04d", "R", 7L), "R:0007"),
    identical(format(1.25, nsmall = 2), "1.25"),
    is.expression(expression),
    identical(eval(expression), 3L),
    identical(deparse1(expression[[1L]]), "1L + 2L")
)
