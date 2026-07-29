# polyglot-covers: r.standard-library.delimited-text-encodings-and-regular-expressions

local({
    root <- tempfile("polyglot-r-text-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    data <- data.frame(id = 1:2, word = c("café", "東京"))
    path <- file.path(root, "data.csv")
    write.csv(data, path, row.names = FALSE, fileEncoding = "UTF-8")
    restored <- read.csv(path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
    matches <- regexec("^(?<word>\\p{L}+)-(?<digits>\\d+)$", "café-42", perl = TRUE)
    captures <- regmatches("café-42", matches)[[1L]]
    invalid_pattern <- tryCatch(grepl("(", "text", perl = TRUE), error = identity)

    stopifnot(
        identical(restored, data),
        identical(grepl("^c.*é$", data$word, perl = TRUE), c(TRUE, FALSE)),
        identical(iconv(data$word, from = "UTF-8", to = "UTF-8"), data$word),
        identical(unname(captures), c("café-42", "café", "42")),
        inherits(invalid_pattern, "error"),
        nzchar(Sys.getlocale("LC_CTYPE"))
    )
})

# CSV 解析、字符编码和 PCRE2 模式是三层合同；transliteration 结果依赖平台，课程不锁定它。
