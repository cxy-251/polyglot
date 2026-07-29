# polyglot-covers: r.language.s3-construction-malformed-objects-and-introspection

validate_percentage <- function(x) {
    if (!is.double(x) || anyNA(x) || any(x < 0 | x > 100)) {
        stop("invalid percentage")
    }
    x
}
new_percentage <- function(x) {
    structure(validate_percentage(as.double(x)), class = "percentage")
}

valid <- new_percentage(c(25, 50))
malformed <- structure("not numeric", class = "percentage")

stopifnot(
    identical(unclass(valid), c(25, 50)),
    inherits(malformed, "percentage"),
    identical(typeof(malformed), "character"),
    inherits(tryCatch(validate_percentage(malformed), error = identity), "error")
)

visible_print_methods <- methods("print")
date_method <- getS3method("print", "Date")
method_name <- "print.Date"
stopifnot(
    is.function(date_method),
    method_name %in% as.character(visible_print_methods),
    isTRUE(attr(visible_print_methods, "info")[method_name, "visible"]),
    identical(environmentName(environment(date_method)), "base")
)

# class 属性本身不验证底层表示；可靠 S3 类型需要 constructor 与 validator 形成显式边界。
