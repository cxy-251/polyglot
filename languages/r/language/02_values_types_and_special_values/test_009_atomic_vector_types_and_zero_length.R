# polyglot-covers: r.language.atomic-vectors-absence-and-special-numeric-values

values <- list(
    logical = TRUE,
    integer = 1L,
    double = 1,
    complex = 1 + 2i,
    character = "R",
    raw = as.raw(0xff)
)
typed_missing <- list(NA, NA_integer_, NA_real_, NA_complex_, NA_character_)

stopifnot(
    identical(unname(vapply(values, typeof, "")), names(values)),
    all(vapply(values, length, 0L) == 1L),
    identical(typeof(numeric()), "double"),
    length(numeric()) == 0L,
    is.null(NULL),
    length(NULL) == 0L,
    !is.null(NA),
    length(NA) == 1L,
    identical(vapply(typed_missing, typeof, ""), c(
        "logical", "integer", "double", "complex", "character"
    )),
    all(vapply(typed_missing, is.na, TRUE)),
    is.nan(NaN),
    is.na(NaN),
    !is.nan(NA_real_),
    all(is.infinite(c(Inf, -Inf))),
    identical(1 / 0, Inf),
    identical(Re(1 + 2i), 1),
    identical(Im(1 + 2i), 2)
)

# NULL 是对象缺失；零长度向量仍有类型；NA 是向量元素值。这三者在组合时也保持不同角色。
stopifnot(
    identical(numeric(0) + 1, numeric(0)),
    identical(c(NULL, 1L), 1L),
    identical(list(NULL, integer(0), NA_integer_), list(NULL, integer(0), NA_integer_)),
    identical(is.na(integer(0)), logical(0))
)
