# polyglot-covers: r.language.s3-method-introspection-and-registration-tables

visible_print_methods <- methods("print")
date_method <- getS3method("print", "Date")
method_name <- "print.Date"

stopifnot(
    is.function(date_method),
    method_name %in% as.character(visible_print_methods),
    isTRUE(attr(visible_print_methods, "info")[method_name, "visible"]),
    identical(environmentName(environment(date_method)), "base")
)
