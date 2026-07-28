# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/r/language/08_collection_workflows_and_tabular_data/
# polyglot-related+: test_059_apply_lapply_sapply_and_vapply_contracts.R
#
# 共同问题：iterable 与 iterator 是否分离；缺少协议时采用什么 fallback。
# 对照观察：R 不暴露 next() 式 iterator 对象；索引序列、`lapply` 和 closure 是惯用替代。

make_next <- local({
    index <- 0L
    values <- c("a", "b")
    function() {
        index <<- index + 1L
        if (index > length(values)) return(NULL)
        values[[index]]
    }
})

stopifnot(
    identical(make_next(), "a"),
    identical(make_next(), "b"),
    is.null(make_next())
)
