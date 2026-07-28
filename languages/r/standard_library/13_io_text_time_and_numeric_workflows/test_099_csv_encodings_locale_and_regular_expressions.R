# polyglot-covers: r.standard-library.csv-encodings-locale-and-regular-expressions

local({
    root <- tempfile("polyglot-r-text-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    data <- data.frame(id = 1:2, word = c("café", "東京"))
    path <- file.path(root, "data.csv")
    write.csv(data, path, row.names = FALSE, fileEncoding = "UTF-8")
    restored <- read.csv(path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")

    stopifnot(
        identical(restored, data),
        identical(grepl("^c.*é$", data$word, perl = TRUE), c(TRUE, FALSE)),
        identical(iconv("café", from = "UTF-8", to = "ASCII//TRANSLIT"), "cafe"),
        nzchar(Sys.getlocale("LC_CTYPE"))
    )
})
