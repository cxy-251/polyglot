# polyglot-covers: r.standard-library.file-paths-metadata-and-content

local({
    root <- tempfile("polyglot-r-files-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    nested <- file.path(root, "nested")
    dir.create(nested)
    path <- file.path(nested, "value.txt")
    writeLines("content", path, useBytes = TRUE)
    metadata <- file.info(path)
    digest <- unname(tools::md5sum(path))

    stopifnot(
        identical(readLines(path, warn = FALSE), "content"),
        identical(normalizePath(dirname(path)), normalizePath(nested)),
        isTRUE(metadata$isdir == FALSE),
        identical(metadata$size, 8),
        grepl("^[[:xdigit:]]{32}$", digest)
    )
})

# file.path 是词法组合；normalizePath 与 file.info 访问文件系统；md5sum 按文件字节计算内容摘要。
